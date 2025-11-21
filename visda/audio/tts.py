# visda/audio/tts.py
import subprocess
from pathlib import Path

from ..state import STATE

ROOT = Path(__file__).resolve().parents[2]
PIPER_VOICE = ROOT / "voices" / "en_US-danny-low.onnx"
OUT_WAV = Path("/tmp/visda_tts.wav")


def _piper_say(text: str) -> None:
    """Run Piper CLI to synthesize and play audio via aplay."""
    if not PIPER_VOICE.is_file():
        print("[tts] no-voice")
        return

    synth_cmd = [
        "piper",
        "--model", str(PIPER_VOICE),
        "--output_file", str(OUT_WAV),
    ]

    try:
        proc = subprocess.run(
            synth_cmd,
            input=text.encode("utf-8"),
            capture_output=False,
        )
    except FileNotFoundError:
        print("[tts] no-piper")
        return
    except Exception:
        print("[tts] err-piper")
        return

    if proc.returncode != 0:
        print("[tts] fail")
        return

    if not OUT_WAV.is_file():
        print("[tts] no-wav")
        return

    play_cmd = ["aplay", str(OUT_WAV)]
    try:
        proc2 = subprocess.run(play_cmd, capture_output=False)
    except FileNotFoundError:
        print("[tts] no-aplay")
        return
    except Exception:
        print("[tts] err-play")
        return

    if proc2.returncode != 0:
        print("[tts] play-fail")


def speak(text: str) -> None:
    """Public TTS entry point used by the rest of the system."""
    if not text:
        return

    with STATE.lock:
        if getattr(STATE, "muted", False):
            print("[tts] muted")
            return
        STATE.tts_busy = True
        STATE.last_spoken = text

    try:
        _piper_say(text)
    finally:
        with STATE.lock:
            STATE.tts_busy = False


if __name__ == "__main__":
    speak("This is VISDA speaking using Piper on the Raspberry Pi.")


