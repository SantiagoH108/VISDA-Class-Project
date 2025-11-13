# file: object.py   (was yolo_imx708.py)
import os
import time
from typing import Callable, Optional

import cv2
from ultralytics import YOLO
from picamera2 import Picamera2

IMGSZ = 320
CONF = 0.35
RES = (640, 480)      # camera output size
SAVE_EVERY_N = 10     # when headless, save every Nth annotated frame


def run_object_detection(
    on_detect: Optional[Callable[[str], None]] = None,
):
    """
    Main object-detection loop.

    - Grabs frames from the IMX708 via Picamera2
    - Runs YOLOv8n on each frame
    - If `on_detect` is provided, calls it with each UNIQUE label per frame:
        on_detect(label: str)
    """
    have_display = bool(os.environ.get("DISPLAY"))  # false if SSH/headless

    # --- Camera: IMX708 via Picamera2, request 3-channel RGB to avoid 4-channel crash ---
    cam = Picamera2()
    cam.configure(
        cam.create_preview_configuration(
            main={"size": RES, "format": "RGB888"}
        )
    )
    cam.start()
    time.sleep(2)  # let AE/AF/AWB settle

    # --- YOLO ---
    model = YOLO("yolov8n.pt")
    model.fuse()

    t0, n = time.time(), 0

    try:
        while True:
            frame = cam.capture_array()  # RGB (H, W, 3)
            if frame is None:
                continue

            # Run YOLO (expects 3 channels; RGB is fine)
            res = model.predict(
                frame,
                imgsz=IMGSZ,
                conf=CONF,
                verbose=False
            )[0]

            # --- Call the callback with detected labels (once per unique label per frame) ---
            if on_detect is not None and res.boxes is not None:
                # res.names is a dict: class_id -> class_name
                names = res.names
                labels_in_frame = set()

                if res.boxes.cls is not None:
                    for cls_id in res.boxes.cls.tolist():
                        label = names.get(int(cls_id), None)
                        if label is not None:
                            labels_in_frame.add(label)

                for label in labels_in_frame:
                    try:
                        on_detect(label)
                    except Exception as e:
                        # Don't crash detection loop if callback misbehaves
                        print(f"[VISION] Error in on_detect callback: {e}")

            # --- Annotated frame for display / saving ---
            annotated = res.plot()  # BGR image suitable for imshow/imwrite

            n += 1
            if n % 10 == 0:
                fps = n / (time.time() - t0)
                cv2.putText(
                    annotated,
                    f"FPS: {fps:.1f}",
                    (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            if have_display:
                cv2.imshow("YOLOv8 IMX708 (press q to quit)", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                if n % SAVE_EVERY_N == 0:
                    cv2.imwrite(f"out_{n:05d}.jpg", annotated)

    except KeyboardInterrupt:
        print("[VISION] KeyboardInterrupt, stopping detection loop.")
    finally:
        cam.stop()
        if have_display:
            cv2.destroyAllWindows()
        print("[VISION] Camera and windows closed.")


# Optional: allow running this file directly for testing
def _print_detected(label: str):
    print(f"[TEST] Detected: {label}")


if __name__ == "__main__":
    # If you run: python object.py
    # it will just print labels to the console as it detects them.
    run_object_detection(on_detect=_print_detected)
