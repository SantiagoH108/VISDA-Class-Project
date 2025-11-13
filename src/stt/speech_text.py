import pyaudio
from vosk import Model, KaldiRecognizer
import json
import os


def run_speech_to_text():
    """
    Runs continuous STT using Vosk until interrupted.
    Returns the full recognized text.
    """

    current_dir = os.path.dirname(__file__)
    model_path = os.path.join(current_dir, "vosk-model-small-en-us-0.15")
    output_dir = os.path.join(current_dir, "/data")

    print(f"[STT] Loading Vosk model from: {model_path}")
    model = Model(model_path)
    rec = KaldiRecognizer(model, 16000)

    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )

    stream.start_stream()
    print("[STT] Speak now...")

    full_text = ""

    try:
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result_json = json.loads(rec.Result())
                text = result_json.get("text", "")
                if text:
                    print(f"[STT] Recognized: {text}")
                    full_text += text + " "

    except KeyboardInterrupt:
        print("\n[STT] Final Recognized Text:")
        print(full_text.strip())

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "recognized_text.txt")

        with open(output_path, "w") as f:
            f.write(full_text.strip())

    finally:
        try:
            stream.stop_stream()
            stream.close()
        finally:
            p.terminate()

    return full_text.strip()
