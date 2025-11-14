# visda/audio/tts.py
"""
Minimal TTS for VISDA on macOS:
- Uses macOS `say` directly (no Piper, no sounddevice)
- Respects STATE.muted
- Logs everything it does
"""

import platform
import subprocess

from ..state import STATE


def _mac_say(text: str):
    cmd = ["say", text]
    print(f"[TTS] calling: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print("[TTS] Error calling 'say':", e)


def _fallback(text: str):
    # Last resort: just log
    print("[TTS] Fallback (no backend). Would have said:", text)


def speak(text: str):
    """
    Public entry point.

    Usage:
        from visda.audio.tts import speak
        speak("hello")
    """
    if not text:
        return

    with STATE.lock:
        if getattr(STATE, "muted", False):
            print("[TTS] Muted; skipping speech:", text)
            return
        STATE.tts_busy = True
        STATE.last_spoken = text

    try:
        system = platform.system()
        print(f"[TTS] speak() on {system}: '{text}'")
        if system == "Darwin":
            _mac_say(text)
        else:
            _fallback(text)
    finally:
        with STATE.lock:
            STATE.tts_busy = False


if __name__ == "__main__":
    # direct module test: python -m visda.audio.tts
    speak("This is VISDA speaking from the TTS module.")

