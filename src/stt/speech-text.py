import pyaudio
from vosk import Model, KaldiRecognizer
import json
import os

current_dir = os.path.dirname(__file__)
model_path = os.path.join(current_dir,".../Models/vosk-model-small-en-us-0.15")
output_dir = os.path.join(current_dir, "../data")

model = Model(model_path)
rec = KaldiRecognizer(model, 16001)

p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)

stream.start_stream()

print("Speak now...")

full_text = ""

try: 
    while True:
        data = stream.read(4001, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result_json = json.loads(rec.Result())
            text = result_json.get("text","")
            if text:
                print("Recognized: ", text)
                full_text += text + " "

except KeyboardInterrupt:

    print("\nFinal Recognized Text: ")
    print(full_text.strip())

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "recognized_text.txt")
    with open("recognized_text.txt", "w") as f:
        f.write(full_text.strip())

finally:
    try:
        stream.stop_stream()
        stream.close()
    finally:
        p.terminate()