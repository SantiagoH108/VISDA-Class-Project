# visda/main.py
# Orchestrates: vision loop + ASR/wake + command handler + Flask web UI

import os
import threading

from .vision.detector import vision_loop
from .audio.asr import wake_listener, asr_after_wake, EVENTS as ASR_EVENTS
from .orchestrator import handle_command, EVENTS as ORCH_EVENTS
from .web.app import create_app
from .audio.tts import speak
from .config import HOST, PORT, YOLO_WEIGHTS, VOSK_MODEL_DIR, PIPER_VOICE


def _bridge_asr_to_orchestrator():
    """Pipe ASR events into the orchestrator."""
    while True:
        ev = ASR_EVENTS.get()
        if ev == "WAKE":
            # start short command window and push the recognized command back as a {"CMD": "..."}
            asr_after_wake()
        elif isinstance(ev, dict) and "CMD" in ev:
            ORCH_EVENTS.put(ev)


def _orchestrator_runner():
    """Consume orchestrator events and speak responses."""
    # Greeting proves TTS path is working (falls back to 'say'/espeak if Piper voice missing)
    speak("System ready. Say VISDA, then ask what is this.")
    while True:
        ev = ORCH_EVENTS.get()
        if isinstance(ev, dict) and "CMD" in ev:
            handle_command(ev["CMD"])


def run():
    """Entry point used by the root runner (python main.py) or python -m visda.main"""
    # --- sanity checks (don’t hard-exit if Piper missing; we can fall back to 'say' / 'espeak') ---
    if not os.path.exists(YOLO_WEIGHTS):
        raise SystemExit(f"Missing YOLO weights at: {YOLO_WEIGHTS}")
    if not os.path.isdir(VOSK_MODEL_DIR):
        raise SystemExit(f"Missing Vosk model dir at: {VOSK_MODEL_DIR}")
    if not os.path.exists(PIPER_VOICE):
        print(f"[WARN] Piper voice not found at {PIPER_VOICE} — will try 'say' (macOS) or 'espeak-ng' fallback.")

    # --- start worker threads ---
    threading.Thread(target=vision_loop, daemon=True).start()
    threading.Thread(target=wake_listener, daemon=True).start()
    threading.Thread(target=_bridge_asr_to_orchestrator, daemon=True).start()
    threading.Thread(target=_orchestrator_runner, daemon=True).start()

    # --- start Flask web app ---
    app = create_app()
    print(f"[WEB] Serving at http://127.0.0.1:{PORT} (and http://<your-ip>:{PORT})")
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    # optional: allows `python -m visda.main` too
    run()


