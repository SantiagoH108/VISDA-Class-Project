# visda/vision/camera.py
import cv2
import time
from ..config import CAM_INDEX, FRAME_W, FRAME_H, FPS_REQ

def _try_open(index, api_pref=None):
    cap = cv2.VideoCapture(index, api_pref) if api_pref is not None else cv2.VideoCapture(index)
    if not cap or not cap.isOpened():
        return None
    # Try MJPG (not always supported on macOS, so ignore failures)
    try: cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
    except: pass
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_FPS,          FPS_REQ)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
    # test grab to confirm
    ok, _ = cap.read()
    if not ok:
        cap.release()
        return None
    return cap

def open_cam():
    # On macOS prefer AVFoundation; on Linux prefer V4L2; otherwise default
    candidates = []

    # First try the configured index with macOS AVFoundation if available
    if hasattr(cv2, "CAP_AVFOUNDATION"):
        candidates.append((CAM_INDEX, cv2.CAP_AVFOUNDATION))

    # Linux V4L2
    if hasattr(cv2, "CAP_V4L2"):
        candidates.append((CAM_INDEX, cv2.CAP_V4L2))

    # Default backend with configured index
    candidates.append((CAM_INDEX, None))

    # Probe a few nearby indices in case the active camera isn’t 0
    for idx in [0,1,2,3]:
        if idx != CAM_INDEX:
            if hasattr(cv2, "CAP_AVFOUNDATION"):
                candidates.append((idx, cv2.CAP_AVFOUNDATION))
            if hasattr(cv2, "CAP_V4L2"):
                candidates.append((idx, cv2.CAP_V4L2))
            candidates.append((idx, None))

    tried = []
    for idx, api in candidates:
        cap = _try_open(idx, api)
        tried.append((idx, api))
        if cap is not None:
            print(f"[CAM] Opened index={idx} api={api}")
            return cap

    msg = "[CAM] Failed to open camera. Tried: " + ", ".join(
        f"(idx={i}, api={a})" for i,a in tried
    )
    raise RuntimeError(msg)

