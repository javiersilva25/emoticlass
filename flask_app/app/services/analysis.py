import os, csv, time, threading, random
from datetime import datetime
from ..extensions import socketio
from .camera import camera_state, camera_lock
from flask import current_app

emotion_mapping = {"happy":"feliz","sad":"triste","angry":"enojado","neutral":"neutral","surprise":"sorpresa","fear":"miedo","disgust":"asco"}
ordered_emotions_es = ["feliz","triste","enojado","neutral","sorpresa","miedo","asco"]

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

def get_temperature_valpo():
    return round(random.uniform(10.0, 25.0), 1)

def _sanitize(name):  # simple
    import re
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

def _now():
    n = datetime.now()
    return {"fecha": n.strftime("%Y-%m-%d"), "hora": n.strftime("%H:%M:%S")}

def _group_cognitive_load(list_emotions):
    if not list_emotions: return 0
    w = {"triste":8,"enojado":7,"miedo":6,"asco":5,"sorpresa":2,"neutral":0,"feliz":-3}
    vals = []
    for em in list_emotions:
        s = sum((em.get(k,0)/100)*w.get(k,0) for k in w)
        vals.append(max(0, min(100, s)))
    return round(sum(vals)/len(vals), 1)

def analyze_faces_thread(academic_config):
    last = 0; INTERVAL = 0.5; TH = 70.0
    date = datetime.now().strftime("%Y-%m-%d")
    fname = f"{date}_{_sanitize(academic_config.get('materia','SinAsignatura'))}_{_sanitize(academic_config.get('grado','SinCurso'))}.csv"
    csv_dir = current_app.config["CSV_DIR"]; os.makedirs(csv_dir, exist_ok=True)
    path = os.path.join(csv_dir, fname)
    header = ["fecha","hora","sexo","emocion","porcentaje","curso","grado","materia","temperatura"]
    if not os.path.exists(path):
        with open(path,"w",newline="",encoding="utf-8") as f: csv.writer(f).writerow(header)

    while True:
        with camera_lock:
            if not camera_state["is_running"]: break
            frame = camera_state["current_frame"].copy() if camera_state["current_frame"] is not None and (time.time()-last>INTERVAL) else None
            if frame is not None: last = time.time()
        if frame is None: time.sleep(0.1); continue

        try:
            if not DEEPFACE_AVAILABLE: continue
            results = DeepFace.analyze(img_path=frame, actions=['emotion','gender'], enforce_detection=False, detector_backend='opencv')
            if not results or results[0].get('face_confidence',0) <= 0:
                socketio.emit("emotion_update", {"face_count": 0}); continue

            rows = []; ts = _now()
            for face in results:
                gender = "Mujer" if face.get('dominant_gender','N/A') == "Woman" else "Hombre"
                base = [ts["fecha"], ts["hora"], gender]
                acad = [academic_config.get('nivel_ensenanza',''),
                        academic_config.get('grado',''),
                        academic_config.get('materia',''),
                        academic_config.get('temperatura','')]
                emotions_es = {emotion_mapping.get(k,k): v for k,v in face.get('emotion',{}).items()}
                for em in ordered_emotions_es:
                    rows.append(base + [em, round(emotions_es.get(em,0.0),2)] + acad)
            with open(path,"a",newline="",encoding="utf-8") as f: csv.writer(f).writerows(rows)

            high = [f for f in results if f.get('emotion',{}).get(f.get('dominant_emotion'),0)>=TH]
            if not high:
                socketio.emit("emotion_update", {"face_count": 0}); continue

            by_type = {e: [] for e in ordered_emotions_es}
            for f in high:
                emo = {emotion_mapping.get(k,k): v for k,v in f.get('emotion',{}).items()}
                for e in ordered_emotions_es: by_type[e].append(float(emo.get(e,0.0)))
            med = {e: sorted(v)[len(v)//2] for e,v in by_type.items() if v}
            dom = max(med, key=med.get, default="neutral"); conf = med.get(dom,0)
            load = _group_cognitive_load([f['emotion'] for f in high])
            socketio.emit("emotion_update", {
                "emotion": dom, "value": float(conf), "cognitive_load": float(load),
                "emotion_values": {k: float(v) for k,v in med.items()}, "face_count": len(high)
            })
        except Exception as e:
            print(f"[analysis] error: {e}")
