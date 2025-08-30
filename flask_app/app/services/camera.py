import cv2
import time
import threading
import numpy as np

# Estado de la cámara
camera_state = {
    "camera_object": None,
    "current_frame": None,
    "camera_index": -1,
    "resolution": None,
    "is_running": False
}

camera_lock = threading.Lock()

# Función para detectar cámaras
def detect_cameras(max_idx=10):  # Aumenté max_idx a 10
    detected_cameras = []
    for i in range(max_idx):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            detected_cameras.append(i)
            cap.release()  # Libera la cámara después de verificarla
    return detected_cameras

# Función para abrir la cámara
def _open_camera(index, resolution):
    cap = cv2.VideoCapture(index, cv2.CAP_ANY)  # Usar el backend por defecto
    if cap.isOpened():
        w, h = map(int, resolution.split("x"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        
        # Verifica la resolución establecida
        actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Configurada resolución: {w}x{h}. Resolución actual: {actual_w}x{actual_h}")
        
        return cap
    return None


# Función que maneja el hilo de la cámara
def camera_thread_func():
    last_idx, last_res = -1, ""
    while True:
        with camera_lock:
            if not camera_state["is_running"]:
                if camera_state["camera_object"] is not None:
                    camera_state["camera_object"].release()
                    camera_state["camera_object"] = None
                break
            idx = camera_state["camera_index"]
            res = camera_state["resolution"]
        
        if idx != last_idx or res != last_res:
            if camera_state["camera_object"] is not None:
                camera_state["camera_object"].release()
            camera_state["camera_object"] = _open_camera(idx, res)
            last_idx, last_res = idx, res
        
        cap = camera_state["camera_object"]
        if cap is not None and cap.isOpened():
            ok, frame = cap.read()
            with camera_lock:
                camera_state["current_frame"] = frame if ok else None
        else:
            with camera_lock:
                camera_state["current_frame"] = None
        time.sleep(1 / 30)

# Función que genera los frames para la transmisión
def generate_frames():
    while True:
        with camera_lock:
            running = camera_state["is_running"]
            frame = camera_state["current_frame"].copy() if camera_state["current_frame"] is not None else None
        
        if not running:
            break
        if frame is None:
            black = np.zeros((480, 640, 3), dtype=np.uint8)
            ok, buf = cv2.imencode(".jpg", black)
        else:
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        if ok:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        
        time.sleep(0.03)
