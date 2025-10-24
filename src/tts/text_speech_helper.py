import os
import wave
from piper import PiperVoice

# Load the voice once at import time for efficiency
_base_dir = os.path.dirname(__file__)
_model_path = os.path.abspath(os.path.join(_base_dir, "../..", "en_US-danny-low.onnx"))

print(f"[TTS] Loading model from: {_model_path}")
_voice = PiperVoice.load(_model_path)
print("[TTS] Model loaded successfully!")

def speak(text: str, filename: str = "output.wav") -> str:
    """
    Convert text to speech and saves as WAV file
    """
    output_path = os.path.abspath(filename)
    with wave.open(output_path, "wb") as wav_file:
        _voice.synthesize_wav(text, wav_file)
    print(f"[TTS] Saved speech to: {output_path}")
    return output_path
