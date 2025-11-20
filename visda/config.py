import os, platform, shutil
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def P(*p): return os.path.join(BASE, *p)

# Models / assets
YOLO_WEIGHTS     = os.environ.get("VISDA_YOLO",   P("weights","yolov8n.pt"))
VOSK_MODEL_DIR   = os.environ.get("VISDA_VOSK",   P("models","vosk-model-small-en-us-0.15"))
PIPER_VOICE      = os.environ.get("VISDA_VOICE",  P("voices","en_US-danny-low.onnx"))
PIPER_BIN        = shutil.which("piper") or ""

# Camera
CAM_INDEX   = int(os.environ.get("VISDA_CAM_INDEX", "0"))
FRAME_W, FRAME_H, FPS_REQ = 640, 480, 24
IMGSZ       = int(os.environ.get("VISDA_IMGSZ", "512"))
CONF_THRES  = float(os.environ.get("VISDA_CONF", "0.35"))

# ASR
SAMPLE_RATE = 44100
BLOCKSIZE   = 8000
POST_WAKE_SEC = float(os.environ.get("VISDA_POST_WAKE", "6.0"))
INPUT_HINT  = os.environ.get("VISDA_INPUT_HINT", "")  # mic name contains this

# Web
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))
