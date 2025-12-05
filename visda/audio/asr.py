# visda/audio/asr.py
import time
import json
import threading
from queue import Queue

import numpy as np
import sounddevice as sd
import vosk
from rapidfuzz import fuzz

from ..state import STATE
from ..config import SAMPLE_RATE, BLOCKSIZE, POST_WAKE_SEC, VOSK_MODEL_DIR
from .tts import speak

EVENTS: Queue = Queue()

WAKE_ALTS = ["visda", "vis d a", "vis-da", "visdah", "vizda", "vista", "this does", "this", "does", "vistar"]

WAKE_THRESH = 70
MIN_RMS = 60
WAKE_REFRACTORY_SEC = 1.5

WAKING = threading.Event()
LAST_WAKE_TS = 0.0
WAKE_STREAM_OPEN = threading.Event()


def _choose_input_device():
    devs = sd.query_devices()
    idx = None

    for i, d in enumerate(devs):
            if d.get("max_input_channels", 0) > 0:
                idx = i
                break
    if idx is None:
        raise RuntimeError("no-mic")
    sd.default.device = (idx, None)
    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = 1
    print(f"[asr] dev={idx}")

def _heard_wake(text: str) -> bool:
    t = (text or "").lower().strip()
    if not t:
        return False
    if "visda" in t or "vista" in t or "this does" in t:
        return True
    for w in WAKE_ALTS:
        if fuzz.partial_ratio(t, w) >= WAKE_THRESH:
            return True
    return False


def wake_listener():
    _choose_input_device()

    try:
        model = vosk.Model(VOSK_MODEL_DIR)
    except Exception:
        print("[asr] no-model")
        return

    wake_grammar = json.dumps(WAKE_ALTS)
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE, wake_grammar)

    baseline = [80.0]
    last_rms_print = [0.0]

    def cb(indata, frames, tinfo, status):
        global LAST_WAKE_TS

        if WAKING.is_set():
            return

        with STATE.lock:
            if STATE.tts_busy:
                return

        mono = indata[:, 0] if indata.ndim == 2 else indata
        rms = float(np.sqrt(np.mean(mono.astype(np.float32) ** 2)) + 1e-9)

        b = baseline[0]
        if rms < 300:
            baseline[0] = b * 0.98 + rms * 0.02
            baseline[0] = max(40.0, min(120.0,baseline[0]))

        gate = max(MIN_RMS, baseline[0] * 2.5)

        now = time.time()
        if now - last_rms_print[0] > 2.0:
            print(f"[asr] r={int(rms)} g={int(gate)}")
            last_rms_print[0] = now

        if rms < gate:
            return

        fired = False
        if rec.AcceptWaveform(mono.tobytes()):
            txt = json.loads(rec.Result()).get("text", "").lower().strip()
            if txt:
                with STATE.lock:
                    STATE.last_asr_partial = txt
                fired = _heard_wake(txt)
        else:
            part = json.loads(rec.PartialResult()).get("partial", "").lower().strip()
            if part:
                with STATE.lock:
                    STATE.last_asr_partial = part
                fired = _heard_wake(part)

        if fired and (not WAKING.is_set()) and (now - LAST_WAKE_TS > WAKE_REFRACTORY_SEC):
            LAST_WAKE_TS = now
            print("[wake]")
            with STATE.lock:
                STATE.wake_count += 1
            WAKING.set()
            EVENTS.put("WAKE")

    print("[asr] listen")
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="int16",
            channels=1,
            callback=cb,
        ):
            WAKE_STREAM_OPEN.set()
            while not WAKING.is_set():
                time.sleep(0.05)
    except sd.PortAudioError:
        print("[asr] pa-err")
    finally:
        WAKE_STREAM_OPEN.clear()
        print("[asr] stop")
    while WAKING.is_set():
        time.sleep(0.05)


def asr_after_wake():
    WAKING.set()

    speak("Hello there.")
    time.sleep(0.2)

    for _ in range(100):
        if not WAKE_STREAM_OPEN.is_set():
            break
        time.sleep(0.01)

    try:
        _choose_input_device()
        model = vosk.Model(VOSK_MODEL_DIR)
    except Exception:
        print("[asr] cmd-no-model")
        WAKING.clear()
        return

    grammar = '["what is this", "what\'s this", "identify", "repeat", "mute", "unmute", "this"]'
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE, grammar)

    t_end = time.time() + POST_WAKE_SEC
    print("[asr] cmd")

    best_partial = ""
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="int16",
            channels=1,
        ) as stream:
            while time.time() < t_end:
                indata, _ = stream.read(BLOCKSIZE)
                mono = indata[:, 0] if indata.ndim == 2 else indata
                if rec.AcceptWaveform(mono.tobytes()):
                    txt = json.loads(rec.Result()).get("text", "").lower().strip()
                    if txt:
                        print("[cmd]", txt)
                        with STATE.lock:
                            STATE.last_asr_final = txt
                        EVENTS.put({"CMD": txt})
                        return
                else:
                    best_partial = json.loads(rec.PartialResult()).get("partial", "") or best_partial
                    if best_partial:
                        with STATE.lock:
                            STATE.last_asr_partial = best_partial
    except sd.PortAudioError:
        print("[asr] cmd-pa-err")
        return
    finally:
        WAKING.clear()

    if best_partial:
        print("[cmd]", best_partial)
        EVENTS.put({"CMD": best_partial})

