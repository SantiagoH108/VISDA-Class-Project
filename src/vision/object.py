import cv2, time
from ultralytics import YOLO

IMGSZ = 320
CONF = 0.35
RES = (640, 480)

def open_logitech():
    for idx in [0,1,2]:
        cap = cv2.VideoCapture(idx, cv2.CAP_ANY)
        if cap.isOpened():
            fourcc = cv2.VideoWriter.fourcc(*'MJPG')
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, RES[0])
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, RES[1])
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
        raise RuntimeError("No Webcam Found")

def main():
    cap = open_logitech()
    model = YOLO("yolov8n.pt"); 
    model.fuse()
    t0, n = time.time(), 0
    
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        res = model.predict(frame, imgsz=IMGSZ, conf=CONF, verbose=False)[0]
        annotated_frame = res[0].plot()

        n += 1
        if n% 10 == 0:
            fps = n/(time.time() - t0)
            cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10,24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        cv2.imshow("Live Feed", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break
    cap.release() 
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()  