<div align="center">

<h1>Project VISDA</h1>
<h3>Vision-Integrated Speech and Detection Apparatus</h3>

<p>A wearable, voice-activated smart helmet combining real-time object detection, offline speech recognition, and text-to-speech — built on a 3D-printed helmet and powered by a Raspberry Pi 5.</p>

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Raspberry_Pi_5-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white"/>
<img src="https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black"/>
<img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/Arduino-00979D?style=for-the-badge&logo=arduino&logoColor=white"/>

<br/><br/>

<p><i>By Thomas Danielsen · Juanpablo Garces · Santiago Henao Rojas · Aidan Stelling</i></p>

</div>

---

## What is VISDA?

VISDA is a **multimodal wearable system** embedded inside a fully custom 3D-printed helmet. It sees, listens, thinks, and speaks — all on-device with no cloud dependency. Point it at an object, say *"VISDA, what is this?"* and it tells you what it sees out loud.

```
┌─────────────────────────────────────────────────────────────────┐
│                        VISDA Pipeline                           │
│                                                                 │
│  Pi Camera 3          Microphone                                │
│      │                    │                                     │
│      ▼                    ▼                                     │
│  YOLOv8n            Vosk ASR (offline)                          │
│  Object Detection   Wake Word Detection                         │
│      │                    │                                     │
│      └──────────┬─────────┘                                     │
│                 ▼                                               │
│          Orchestrator                                           │
│     "This looks like [label]"                                   │
│                 │                                               │
│                 ▼                                               │
│          Piper TTS → WAV → aplay → Speaker                      │
│                                                                 │
│  Flask Dashboard ← live video + detection table (local network) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Hardware

| Component | Spec |
|-----------|------|
| Main Computer | Raspberry Pi 5 (8GB RAM) |
| Camera | Pi Camera 3 |
| Microcontroller | Arduino Nano |
| Ultrasonic Sensor | HC-SR04 |
| Visor Servos | 2× SG-90 Micro Servo |
| Helmet | 3D-printed, Ender 3 S1, Elegoo PLA+ Grey |
| Finishing | Bondo Spot Putty + Rust-Oleum 2x Gray Primer |

The Arduino Nano is mounted at the rear of the helmet alongside the Raspberry Pi, dedicated to driving the HC-SR04 ultrasonic sensor and the two SG-90 servos that open and close the visor. Keeping these on a separate controller prevents PWM timing conflicts with the Pi's main processing threads.

---

## Object Detection

Runs **YOLOv8n** (nano) with a pretrained COCO dataset on the Raspberry Pi 5 in a continuous background thread.

```python
# Vision loop (simplified)
while True:
    ok, frame = cap.read()
    res = model.predict(frame, imgsz=IMGSZ, conf=CONF_THRES, verbose=False)[0]
    dets = []
    for b in res.boxes:
        x1,y1,x2,y2 = b.xyxy[0].tolist()
        cls   = int(b.cls[0])
        conf  = float(b.conf[0])
        label = res.names[cls]
        dets.append((label, conf, (x1,y1,x2,y2)))
```

**Closest object selection:** each detection is scored by bounding box area and distance from frame center. The highest-scoring detection triggers the speech output: *"This looks like [label]."*

- Frame resolution: 640×480
- Configurable: `IMGSZ`, `CONF_THRES`
- Runs as a daemon thread alongside voice and Flask threads

---

## Voice Interaction Pipeline

All speech processing runs **fully offline** on the Raspberry Pi — no API calls, no internet required.

### 1 — Wake Word Detection
Microphone audio streams continuously into **Vosk ASR**. The wake listener monitors for `"VISDA"` and common variants (`"this"`, `"does"`, `"this does"`) with adaptive noise gating (`MIN_RMS = 60`, `WAKE_THRESH = 70`, `WAKE_REFRACTORY_SEC = 1.5`). When matched, the system enters command mode.

### 2 — Command Recognition (STT)
After wake, Vosk switches to a grammar-restricted recognizer to improve accuracy. Recognized commands include `"what is this"`, `"identify"`, `"this"`. The command is dispatched to the orchestrator which fetches the latest YOLO detections and generates a response string.

### 3 — Text-to-Speech Output (TTS)
The response is passed to **Piper TTS** — a lightweight neural TTS engine optimized for Raspberry Pi. Piper synthesizes to a WAV file which the Pi plays back via ALSA (`aplay`) through an onboard speaker.

```python
# Threads run in parallel — all daemon threads
threading.Thread(target=vision_loop,      daemon=True).start()
threading.Thread(target=wake_listener,    daemon=True).start()
threading.Thread(target=bridge_asr_to_orch, daemon=True).start()
threading.Thread(target=orch_loop,        daemon=True).start()
```

---

## Flask Web Dashboard

A local Flask server runs on the Pi and serves a real-time monitoring dashboard accessible from any device on the same network.

```python
@app.get("/status")
def status():
    with STATE.lock:
        data = dict(fps=STATE.fps, dets=STATE.dets[:8])
    return jsonify(data)

@app.get("/video")
def video():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
```

**Dashboard features:**
- Live MJPEG video stream with YOLOv8 bounding box overlays
- Detection table showing label + confidence for each object in frame
- Lightweight minimal UI — designed to minimize CPU overhead on the Pi

![Flask Dashboard](assets/flask_dashboard.png)

---

## Visor — Ultrasonic Servo Control

The visor opens and closes automatically based on proximity data from the HC-SR04 ultrasonic sensor, controlled by the Arduino Nano driving two SG-90 servos. This keeps servo PWM management completely off the Raspberry Pi's main processing pipeline.

---

## Build Photos

<table>
<tr>
<td><img src="assets/helmet_rear.png" alt="Raspberry Pi mounted on helmet rear"/></td>
<td><img src="assets/helmet_interior.png" alt="Servo wiring inside helmet"/></td>
<td><img src="assets/helmet_front.png" alt="Completed helmet front view"/></td>
</tr>
<tr>
<td align="center">Raspberry Pi + Arduino at rear</td>
<td align="center">SG-90 servos inside visor</td>
<td align="center">Finished helmet</td>
</tr>
</table>

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Object Detection | YOLOv8n (Ultralytics) |
| Speech Recognition | Vosk (offline neural ASR) |
| Text-to-Speech | Piper TTS |
| Web Dashboard | Flask + OpenCV MJPEG |
| Audio Playback | ALSA (`aplay`) |
| Servo / Ultrasonic | Arduino Nano + HC-SR04 + SG-90 |
| 3D Modeling | Autodesk Meshmixer |
| 3D Printing | Ender 3 S1 + Elegoo PLA+ |
| Concurrency | Python `threading` (daemon threads) |

---

## Limitations

**Hardware**
- Onboard microphone quality insufficient for clear real-time capture in noisy environments
- Speaker size prevented full integration inside the helmet shell

**Physical**
- Visor geometry is generalized — does not conform precisely to helmet curvature without interfering with internal wiring

**Software**
- YOLOv8 FPS degrades as scene complexity increases on the Pi 5's CPU; no GPU acceleration available on-device

---

## Repository Structure

```
.
├── visda_main.py          Main entry point — starts all threads
├── vision.py              YOLOv8 detection loop
├── asr.py                 Vosk wake word + command recognition
├── tts.py                 Piper TTS output module
├── orchestrator.py        Command → detection → response logic
├── flask_app.py           Flask dashboard server
├── arduino/
│   └── visor_control.ino  HC-SR04 + SG-90 servo control
└── assets/
    ├── flask_dashboard.png
    ├── helmet_front.png
    ├── helmet_rear.png
    └── helmet_interior.png
```

---

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Object_Detection-00FFFF?style=flat-square)
![Vosk](https://img.shields.io/badge/Vosk-Offline_ASR-informational?style=flat-square)
![Piper](https://img.shields.io/badge/Piper-Neural_TTS-orange?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-Live_Dashboard-black?style=flat-square)
![Arduino](https://img.shields.io/badge/Arduino-Servo_Control-00979D?style=flat-square)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi_5-Embedded-C51A4A?style=flat-square)

</div>