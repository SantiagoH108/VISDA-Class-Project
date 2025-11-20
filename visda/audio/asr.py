# visda/audio/asr.py
import os
import time
import json
import threading
from queue import Queue

import numpy as np
import sounddevice as sd
import vosk
from rapidfuzz import fuzz

from ..state import STATE
from ..config import SAMPLE_RATE, BLOCKSIZE, POST_WAKE_SEC, INPUT_HINT, VOSK_MODEL_DIR
from .tts import speak

EVENTS: Queue = Queue()

WAKE_ALTS   = ["this", "does", "this does", "visda", "vis d a", "vis-da", "visdah", "vizda", "vista", "bizda", "vistar"]
WAKE_THRESH = 70 
MIN_RMS     = 60 
WAKE_REFRACTORY_SEC = 1.5

WAKING = threading.Event()
LAST_WAKE_TS = 0.0
WAKE_STREAM_OPEN = threading.Event()

def _choose_input_device():
    devs = sd.query_devices()
    idx = None
    if INPUT_HINT:
        for i, d in enumerate(devs):
            if d.get("max_input_channels", 0) > 0 and INPUT_HINT.lower() in d.get("name", "").lower():
                idx = i
                break
    if idx is None:
        for i, d in enumerate(devs):
            if d.get("max_input_channels", 0) > 0:
                idx = i
                break
    if idx is None:
        raise RuntimeError("No input device with input channels found.")
    sd.default.device = (idx, None)
    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = 1
    print(f"[ASR] Using input device idx={idx} ({devs[idx]['name']}) @ {SAMPLE_RATE} Hz")


def _heard_wake(text: str) -> bool:
    t = (text or "").lower().strip()
    if not t:
        return False

    # Direct match on what the model can actually output
    if "vista" in t or "this does" in t:
        return True

    # fuzzy backup (but now only over WAKE_ALTS that actually exist)
    for w in WAKE_ALTS:
        if fuzz.partial_ratio(t, w) >= 60:
            return True

    return False



def wake_listener():
    """Continuously listens for the wake word. On detection, puts 'WAKE' in EVENTS."""
    _choose_input_device()
    try:
        model = vosk.Model(VOSK_MODEL_DIR)
    except Exception as e:
        print("[ASR] Failed to load Vosk model:", e)
        return

    wake_grammar = json.dumps(WAKE_ALTS)
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE, wake_grammar)

    # adaptive baseline for room noise (simple EMA)
    baseline = [80.0]  # mutable holder in closure

    def cb(indata, frames, tinfo, status):
        global LAST_WAKE_TS

        # If we're in the post-wake command phase, don't process audio here
        if WAKING.is_set():
            return

        # Don't listen while speaking TTS to avoid self-trigger
        with STATE.lock:
            if STATE.tts_busy:
                return

        # mono int16 -> rms
        mono = indata[:, 0] if indata.ndim == 2 else indata
        rms = float(np.sqrt(np.mean(mono.astype(np.float32) ** 2)) + 1e-9)

        # update baseline slowly when quiet
        b = baseline[0]
        if rms < max(200, b * 1.2):           # "quiet" samples nudge the baseline
            baseline[0] = b * 0.98 + rms * 0.02

        # adaptive gate: speech must exceed both MIN_RMS and N×baseline
        gate = max(MIN_RMS, baseline[0] * 2.5)

        # lightweight periodic debug
        if int(time.time() * 2) % 10 == 0:
            print(f"[ASR] rms={rms:.0f} base={baseline[0]:.0f} gate={gate:.0f}")

        if rms < gate:
            return

        fired = False
        if rec.AcceptWaveform(mono.tobytes()):
            txt = json.loads(rec.Result()).get("text", "").lower().strip()
            if txt:
                print("[ASR FINAL]", txt)
                with STATE.lock:
                    STATE.last_asr_partial = txt
                fired = _heard_wake(txt)
        else:
            part = json.loads(rec.PartialResult()).get("partial", "").lower().strip()
            if part and part != getattr(cb, "_last_part", ""):
                print("[ASR PART ]", part)
                cb._last_part = part
                with STATE.lock:
                    STATE.last_asr_partial = part
            fired = _heard_wake(part)

        now = time.time()
        if fired and (not WAKING.is_set()) and (now - LAST_WAKE_TS > WAKE_REFRACTORY_SEC):
            LAST_WAKE_TS = now
            print("[WAKE] detected")
            # tiny chime on macOS (best-effort)
            try:
                import platform, subprocess
                if platform.system() == "Darwin":
                    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            except Exception:
                pass
            with STATE.lock:
                STATE.wake_count += 1

            # IMPORTANT: mark that we're entering post-wake phase
            WAKING.set()
            EVENTS.put("WAKE")

    print("[INIT] wake listener (fuzzy + adaptive) running")
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                            channels=1, callback=cb):
            # Mark that the wake InputStream is actually open
            WAKE_STREAM_OPEN.set()
            # Run until something sets WAKING (wake word fired)
            while not WAKING.is_set():
                time.sleep(0.05)
    except sd.PortAudioError as e:
        print("[ASR] PortAudioError in wake_listener:", e)
    finally:
        WAKE_STREAM_OPEN.clear()
        print("[ASR] wake listener stream closed")




def asr_after_wake():
    """Listen for a short command after wake and emit {'CMD': text}."""
    # signal we're in post-wake mode (used by wake_listener)
    WAKING.set()

    speak('Hello there.')
    time.sleep(0.2)
    # Wait briefly for wake_listener to actually release the mic
    for _ in range(100):  # up to ~1s (100 * 10ms)
        if not WAKE_STREAM_OPEN.is_set():
            break
        time.sleep(0.01)

    try:
        _choose_input_device()
        model = vosk.Model(VOSK_MODEL_DIR)
    except Exception as e:
        print("[ASR] Failed to init command recognizer:", e)
        WAKING.clear()
        return

    # Small grammar biases decoding to your commands
    grammar = '["what is this", "what\'s this", "identify", "repeat", "mute", "unmute", "this"]'
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE, grammar)

    t_end = time.time() + POST_WAKE_SEC
    print(f"[ASR] listening for command {POST_WAKE_SEC:.1f} sec")

    best_partial = ""
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                            channels=1) as stream:
            while time.time() < t_end:
                indata, _ = stream.read(BLOCKSIZE)
                mono = indata[:, 0] if indata.ndim == 2 else indata
                if rec.AcceptWaveform(mono.tobytes()):
                    txt = json.loads(rec.Result()).get("text", "").lower().strip()
                    if txt:
                        print("[CMD]", txt)
                        with STATE.lock:
                            STATE.last_asr_final = txt
                        EVENTS.put({"CMD": txt})
                        return
                else:
                    best_partial = json.loads(rec.PartialResult()).get("partial", "") or best_partial
                    if best_partial:
                        with STATE.lock:
                            STATE.last_asr_partial = best_partial
    except sd.PortAudioError as e:
        print("[ASR] PortAudioError in asr_after_wake:", e)
        return
    finally:
        # make sure we always leave post-wake mode
        WAKING.clear()

    # if we got here, timeout but we might have a decent partial
    if best_partial:
        EVENTS.put({"CMD": best_partial})
