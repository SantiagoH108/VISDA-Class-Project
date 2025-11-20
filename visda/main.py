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
        try:
            ev = ASR_EVENTS.get()
            print("[BRIDGE] got ASR event:", ev)

            if ev == "WAKE":
                try:
                    # Run the short post-wake ASR window
                    asr_after_wake()
                except Exception as e:
                    print("[BRIDGE] asr_after_wake crashed:", repr(e))
                finally:
                    # After command phase ends (or fails), re-arm the wake listener
                    threading.Thread(target=wake_listener, daemon=True).start()

            elif isinstance(ev, dict) and "CMD" in ev:
                print("[BRIDGE] forwarding CMD to orchestrator:", ev["CMD"])
                ORCH_EVENTS.put(ev)

            else:
                print("[BRIDGE] unknown event:", ev)

        except Exception as e:
            # This protects the *bridge loop itself* from dying
            print("[BRIDGE] unexpected error in loop:", repr(e))
            # then continue to the next event
            continue




def _orchestrator_runner():
    """Consume orchestrator events and speak responses."""
    # Greeting proves TTS path is working (falls back to 'say'/espeak if Piper voice missing)
    speak("System ready. Say VISDA, then ask what is this.")
    while True:
        ev = ORCH_EVENTS.get()
        if isinstance(ev, dict) and "CMD" in ev:
            handle_command(ev["CMD"])


def run():
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


