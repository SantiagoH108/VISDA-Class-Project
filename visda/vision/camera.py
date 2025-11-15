import cv2
from picamera2 import Picamera2

try:
    from ..config import FRAME_W, FRAME_H
except ImportError:
    FRAME_W, FRAME_H = 640,480

class PiCam:
    def __init__(self):
        self.picam =Picamera2()
        config = self.picam.create_preview_configuration(main={"size": (FRAME_W, FRAME_H), "format": "RGB888"})
        self.picam.configure(config)
        self.picam.start()
        self._opened = True

    def isOpened(self):
        return self._opened
    
    def read(self):
        if not self._opened:
            return False, None
        rgb = self.picam.capture_array()
        frame_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        return True, frame_bgr
    
    def release(self):
        if self._opened:
            self.picam.stop()
            self._opened = False

def open_cam():
    cam = PiCam()
    if not cam.isOpened():
        raise RuntimeError("Picam failed")
    return cam
    



