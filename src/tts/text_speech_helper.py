import os
import wave
import subprocess
from piper import PiperVoice

# Load the voice once at import time for efficiency
_base_dir = os.path.dirname(__file__)
_model_path = os.path.abspath(os.path.join(_base_dir, "../..", "en_US-danny-low.onnx"))

print(f"[TTS] Loading model from: {_model_path}")
_voice = PiperVoice.load(_model_path)
print("[TTS] Model loaded successfully!")

def speak(text: str, filename: str = "output.wav", play: bool = True) -> str:
    """
    Convert text to speech and saves as WAV file
    """
    output_path = os.path.abspath(filename)

    # Generate speech
    with wave.open(output_path, "wb") as wav_file:
        _voice.synthesize_wav(text, wav_file)
    print(f"[TTS] Saved speech to: {output_path}")

    # Auto-play on Raspberry Pi using aplay
    if play:
        try:
            subprocess.Popen(["aplay", output_path])
        except FileNotFoundError:
            print("[TTS] Could not play audio. 'aplay' not found. Install with 'sudo apt install alsa-utils'.")

    return output_path
