import pyaudio
from vosk import Model, KaldiRecognizer
import json

model = Model("vosk-model-small-en-us-0.15")
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

    with open("recognized_text.txt", "w") as f:
        f.write(full_text.strip())
