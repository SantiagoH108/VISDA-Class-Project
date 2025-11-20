import subprocess
from pathlib import Path

from ..state import STATE

# Path to your Piper voice model (.onnx)
# Adjust this if your file is named or located differently.
ROOT = Path(__file__).resolve().parents[2]
PIPER_VOICE = ROOT / "voices" / "en_US-danny-low.onnx"
OUT_WAV = Path("/tmp/visda_tts.wav")


def _piper_say(text: str) -> None:
    """Run Piper CLI to synthesize and then play the audio."""
    if not PIPER_VOICE.is_file():
        print(f"[TTS] Piper voice not found at {PIPER_VOICE}")
        return

    synth_cmd = [
        "piper",
        "--model",
        str(PIPER_VOICE),
        "--output_file",
        str(OUT_WAV),
    ]
    print("[TTS] running:", " ".join(synth_cmd))

    try:
        proc = subprocess.run(
            synth_cmd,
            input=text.encode("utf-8"),
            capture_output=True,
        )
    except FileNotFoundError:
        print("[TTS] 'piper' command not found. Is Piper installed?")
        return
    except Exception as e:
        print("[TTS] Error running piper:", e)
        return

    print("[TTS] piper return code:", proc.returncode)
    if proc.stdout:
        print("[TTS] piper stdout:", proc.stdout.decode(errors="ignore"))
    if proc.stderr:
        print("[TTS] piper stderr:", proc.stderr.decode(errors="ignore"))

    if proc.returncode != 0:
        print(f"[TTS] Piper synth failed with code {proc.returncode}")
        return

    # Make sure file exists
    if not OUT_WAV.is_file():
        print(f"[TTS] Expected WAV not found at {OUT_WAV}")
        return

    # 2) Play with aplay (ALSA)
    play_cmd = ["aplay", "-v", str(OUT_WAV)]  # -v = verbose ALSA output
    print("[TTS] running:", " ".join(play_cmd))
    try:
        proc2 = subprocess.run(
            play_cmd,
            capture_output=True,
        )
    except FileNotFoundError:
        print("[TTS] 'aplay' not found. Install alsa-utils.")
        return
    except Exception as e:
        print("[TTS] Error running aplay:", e)
        return

    print("[TTS] aplay return code:", proc2.returncode)
    if proc2.stdout:
        print("[TTS] aplay stdout:", proc2.stdout.decode(errors="ignore"))
    if proc2.stderr:
        print("[TTS] aplay stderr:", proc2.stderr.decode(errors="ignore"))



def speak(text: str) -> None:
    """Public TTS entry point used by the rest of the system."""
    if not text:
        return

    # Check mute + mark TTS as busy
    with STATE.lock:
        if getattr(STATE, "muted", False):
            print("[TTS] Muted; skipping:", text)
            return
        STATE.tts_busy = True
        STATE.last_spoken = text

    try:
        print(f"[TTS] Piper speaking: '{text}'")
        _piper_say(text)
    finally:
        with STATE.lock:
            STATE.tts_busy = False


if __name__ == "__main__":
    speak("This is VISDA speaking using Piper on the Raspberry Pi.")

