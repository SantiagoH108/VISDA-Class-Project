from .state import STATE
from .audio.tts import speak
from .utils.helpers import pick_closest
from queue import Queue

EVENTS: "Queue[object]" = Queue()

def handle_command(cmd: str):
    t = (cmd or "").lower()
    if "mute" in t and "unmute" not in t:
        with STATE.lock: STATE.muted = True; speak("Muted."); return
    if "unmute" in t:
        with STATE.lock: STATE.muted = False; speak("Unmuted."); return
    if ("what is this" in t) or ("what's this" in t) or ("identify" in t) or (t.strip()=="this"):
        with STATE.lock: dets = list(STATE.dets); h,w = STATE.shape
        if not dets: speak("I don't see anything yet."); return
        best = pick_closest(dets, w, h)
        if not best: speak("I'm not sure."); return
        label, conf, _ = best
        friendly = label.replace("_"," ")
        speak(f"This looks like a {friendly}." if conf >= 0.45 else f"I'm not sure, maybe a {friendly}.")
        return
    speak("Say 'what is this' after VISDA.")
