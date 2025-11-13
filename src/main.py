import time

from tts import talker
from vision.object import run_object_detection
from stt import run_speech_to_text


# --- Simple debouncing for TTS so it doesn't spam the same label ---
_LAST_SPOKEN = {"label": None, "time": 0.0}
SPEAK_MIN_INTERVAL = 3.0  # seconds between repeating the same label


def handle_detected_object(label: str):
    """
    Called by run_object_detection(label_callback=...) whenever an object label is detected.
    Turns labels into spoken sentences, with some simple spam protection.
    """
    if not label:
        return

    label = label.strip()
    if not label:
        return

    now = time.time()

    # avoid saying the same thing over and over very fast
    if (
        _LAST_SPOKEN["label"] == label
        and (now - _LAST_SPOKEN["time"]) < SPEAK_MIN_INTERVAL
    ):
        return

    # pick article
    if label.lower().endswith("s"):
        sentence = f"I am looking at {label}"
    else:
        article = "an" if label[0].lower() in "aeiou" else "a"
        sentence = f"I am looking at {article} {label}"

    talker(sentence)

    _LAST_SPOKEN["label"] = label
    _LAST_SPOKEN["time"] = now


def run_detection_with_tts():
    """
    Wrapper to start the object detection loop with TTS callback.
    This will run until you press Ctrl+C in the terminal.
    """
    print("[MAIN] Starting object detection with TTS. Press Ctrl+C to stop.")
    try:
        # Your object.py should call on_detect(label) from inside its loop.
        run_object_detection(on_detect=handle_detected_object)
    except KeyboardInterrupt:
        print("\n[MAIN] Detection interrupted by user.")
    finally:
        print("[MAIN] Detection loop exited.\n")


def run_stt_test():
    """
    Wrapper to run your speech-to-text loop once.
    This will listen until you interrupt with Ctrl+C.
    """
    print("[MAIN] Starting speech-to-text. Press Ctrl+C to stop listening.")
    try:
        text = run_speech_to_text()
        print("[MAIN] STT finished. Final text:")
        print(text)
    except KeyboardInterrupt:
        print("\n[MAIN] STT interrupted by user.")
    finally:
        print("[MAIN] STT run exited.\n")


def main():
    print("=== VISDA System ===")
    print("Vision + TTS + STT integration")
    while True:
        print("\nSelect an option:")
        print("  1) Run object detection with speech output")
        print("  2) Run speech-to-text (Vosk) test")
        print("  q) Quit")
        choice = input("> ").strip().lower()

        if choice == "1":
            run_detection_with_tts()
        elif choice == "2":
            run_stt_test()
        elif choice == "q":
            print("[MAIN] Exiting VISDA.")
            break
        else:
            print("Unknown option, please choose 1, 2, or q.")


if __name__ == "__main__":
    main()
