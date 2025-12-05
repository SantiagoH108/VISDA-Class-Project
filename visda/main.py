import os
import threading

from visda.vision.detector import vision_loop
from visda.audio.asr import wake_listener, asr_after_wake, EVENTS as ASR_EVENTS
from visda.orchestrator import handle_command, EVENTS as ORCH_EVENTS
from visda.web.app import create_app
from visda.audio.tts import speak
from visda.config import HOST, PORT, YOLO_WEIGHTS, VOSK_MODEL_DIR, PIPER_VOICE


def bridge_asr_to_orch():
     while True:
        ev = ASR_EVENTS.get()

        if ev == "WAKE":
            print("WAKE")
            try:
                asr_after_wake()
            except Exception as e:
                print("error")
            finally:
                threading.Thread(target=wake_listener, daemon=True).start()

        elif isinstance(ev, dict) and "CMD" in ev:
            ORCH_EVENTS.put(ev)
        else:
            pass



def orch_loop():
    speak("System ready. Say VISDA, then ask what is this.")
    while True:
        ev = ORCH_EVENTS.get()

        if isinstance(ev, dict) and "CMD" in ev:
            handle_command(ev["CMD"])


def run():
    #check paths for model files
    if not os.path.exists(YOLO_WEIGHTS):
        raise SystemExit(f"Missing YOLO weights at: {YOLO_WEIGHTS}")
    if not os.path.isdir(VOSK_MODEL_DIR):
        raise SystemExit(f"Missing Vosk model dir at: {VOSK_MODEL_DIR}")
    if not os.path.exists(PIPER_VOICE):
        print(f"[WARN] Piper voice not found at {PIPER_VOICE} — will try 'say' (macOS) or 'espeak-ng' fallback.")

    #starts threads for each action so all can run in parrallel 
    threading.Thread(target=vision_loop, daemon=True).start()
    threading.Thread(target=wake_listener, daemon=True).start()
    threading.Thread(target=bridge_asr_to_orch, daemon=True).start()
    threading.Thread(target=orch_loop, daemon=True).start()

    app = create_app()
    print(f"[WEB] Serving at http://127.0.0.1:{PORT} (and http://<your-ip>:{PORT})")
    app.run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    # optional: allows `python -m visda.main` too
    run()


