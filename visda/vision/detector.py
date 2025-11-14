import time, cv2
from ultralytics import YOLO
from ..state import STATE
from ..config import YOLO_WEIGHTS, IMGSZ, CONF_THRES
from .camera import open_cam

def vision_loop():
    cap = open_cam()
    model = YOLO(YOLO_WEIGHTS)
    try: model.fuse()
    except: pass
    n, t0 = 0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok: continue
        res = model.predict(frame, imgsz=IMGSZ, conf=CONF_THRES, verbose=False)[0]
        dets = []
        for b in res.boxes:
            x1,y1,x2,y2 = b.xyxy[0].tolist()
            cls = int(b.cls[0]); conf = float(b.conf[0]); label = res.names[cls]
            dets.append((label, conf, (x1,y1,x2,y2)))
        n += 1
        fps = (n/(time.time()-t0)) if n%10==0 else STATE.fps
        ann = frame.copy()
        for (label, conf, (x1,y1,x2,y2)) in dets:
            cv2.rectangle(ann,(int(x1),int(y1)),(int(x2),int(y2)),(0,255,0),2)
            cv2.putText(ann,f"{label} {conf:.2f}",(int(x1),max(20,int(y1)-6)),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
        with STATE.lock:
            STATE.frame = ann; STATE.shape = (ann.shape[0], ann.shape[1]); STATE.dets = dets; STATE.fps = fps or 0.0
