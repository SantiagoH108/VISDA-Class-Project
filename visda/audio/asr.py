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

# ---------------- Public queue ----------------
# Emits "WAKE" or {"CMD": "<text>"} that orchestrator consumes.
EVENTS: Queue = Queue()

# ---------------- Wake tuning ----------------
WAKE_ALTS   = ["visda", "vis d a", "vis-da", "visdah", "vizda", "vista", "bizda", "vistar"]
WAKE_THRESH = 70           # fuzzy threshold (0..100); lower == more sensitive
MIN_RMS     = 60           # base gate; adaptive gate raises this dynamically
WAKE_REFRACTORY_SEC = 1.5  # ignore re-triggers for this long

# Internal state flags
WAKING = threading.Event()   # True during post-wake command window
LAST_WAKE_TS = 0.0           # last time we fired wake


# ---------------- Utilities ----------------
def _choose_input_device():
    """Pick a sensible input device; prefer INPUT_HINT if provided."""
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
    """Heuristic/fuzzy match for 'VISDA' and common variants."""
    t = (text or "").lower().strip()
    if not t:
        return False
    # quick contains check for obvious forms
    if any(w in t for w in ["visda", "vis da", "vizda", "vista", "visdah"]):
        return True
    # token-level fuzz
    toks = t.split()
    for tok in toks:
        for w in WAKE_ALTS:
            if fuzz.ratio(tok, w) >= WAKE_THRESH:
                return True
    # whole-string partial
    return fuzz.partial_ratio(t, "visda") >= WAKE_THRESH


# ---------------- Continuous wake listener ----------------
def wake_listener():
    """Continuously listens for the wake word. On detection, puts 'WAKE' in EVENTS."""
    _choose_input_device()
    try:
        model = vosk.Model(VOSK_MODEL_DIR)
    except Exception as e:
        print("[ASR] Failed to load Vosk model:", e)
        return

    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    # adaptive baseline for room noise (simple EMA)
    baseline = [80.0]  # mutable holder in closure

    def cb(indata, frames, tinfo, status):
        global LAST_WAKE_TS
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
            EVENTS.put("WAKE")

    print("[INIT] wake listener (fuzzy + adaptive) running")
    with sd.InputStream(samplerate=SAMPLE_RATE, blocksize=BLOCKSIZE, dtype='int16',
                        channels=1, callback=cb):
        while True:
            time.sleep(0.05)


# ---------------- Post-wake command recognizer ----------------
def asr_after_wake():
    """Listen for a short command after wake and emit {'CMD': text}."""
    WAKING.set()
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
                    WAKING.clear()
                    return
            else:
                best_partial = json.loads(rec.PartialResult()).get("partial", "") or best_partial
                if best_partial:
                    with STATE.lock:
                        STATE.last_asr_partial = best_partial

    if best_partial:
        EVENTS.put({"CMD": best_partial})
