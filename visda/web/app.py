from flask import Flask, Response, jsonify, render_template, request
import cv2, time
from ..state import STATE
from ..audio.tts import speak

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    @app.get("/")
    def index():
        return render_template("index.html")
    

    @app.get("/status")
    def status():
        with STATE.lock:
            dets = STATE.dets[:8]
            data = dict(
                fps=STATE.fps,
                dets=dets,
            )
        return jsonify(data)


    def gen():
        while True:
            with STATE.lock:
                fr = STATE.frame.copy() if STATE.frame is not None else None
            if fr is None:
                time.sleep(0.02); continue
            ok, jpg = cv2.imencode(".jpg", fr, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                   jpg.tobytes() + b"\r\n")

    @app.get("/video")
    def video():
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app



