import cv2
import time
import threading
import numpy as np
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Estado de la cámara
camera_state = {
    "camera_object": None,
    "current_frame": None,
    "camera_index": -1,
    "resolution": None,
    "is_running": False,
    "last_error": None,
    "initialization_success": False
}

camera_lock = threading.Lock()

# Backends prioritarios para Windows
_BACKENDS = [
    cv2.CAP_MSMF,   # Windows Media Foundation (recomendado)
    cv2.CAP_DSHOW,  # DirectShow (backup)
    cv2.CAP_ANY     # Auto-detección como último recurso
]

def _get_backend_name(backend):
    """Obtiene el nombre legible del backend"""
    backend_names = {
        cv2.CAP_MSMF: "MSMF",
        cv2.CAP_DSHOW: "DSHOW",
        cv2.CAP_ANY: "AUTO"
    }
    return backend_names.get(backend, f"UNKNOWN_{backend}")

def _try_open_camera(index, backend, test_read=True):
    """
    Intenta abrir una cámara con un backend específico
    Args:
        index: Índice de la cámara
        backend: Backend de OpenCV a usar
        test_read: Si debe probar leer un frame para validar
    """
    cap = None
    try:
        logger.info(f"Intentando abrir cámara {index} con backend {_get_backend_name(backend)}")
        cap = cv2.VideoCapture(index, backend)
        
        if not cap.isOpened():
            logger.warning(f"Cámara {index} no se pudo abrir con backend {_get_backend_name(backend)}")
            if cap:
                cap.release()
            return None
        
        # Configurar algunas propiedades básicas
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Probar leer un frame si se solicita
        if test_read:
            logger.info(f"Probando lectura de frame para cámara {index}")
            ret, frame = cap.read()
            if not ret or frame is None:
                logger.warning(f"Cámara {index} se abrió pero no puede leer frames")
                cap.release()
                return None
            logger.info(f"✅ Cámara {index} funcionando correctamente con backend {_get_backend_name(backend)}")
        
        return cap
        
    except Exception as e:
        logger.error(f"Error abriendo cámara {index} con backend {_get_backend_name(backend)}: {e}")
        if cap:
            try:
                cap.release()
            except:
                pass
        return None

def detect_cameras(max_idx=10):
    """
    Detecta cámaras disponibles de forma más robusta
    Devuelve lista de índices de cámaras funcionales
    """
    logger.info(f"Detectando cámaras disponibles (máximo índice: {max_idx})")
    detected_cameras = []
    
    for i in range(max_idx):
        for backend in _BACKENDS:
            cap = _try_open_camera(i, backend, test_read=True)
            if cap:
                detected_cameras.append(i)
                cap.release()
                logger.info(f"✅ Cámara detectada en índice {i}")
                break  # Pasar al siguiente índice
        
        # Si no se detectó ninguna cámara real, agregar índice 0 como demo
        if i == 0 and len(detected_cameras) == 0:
            logger.warning("No se detectaron cámaras reales, agregando índice 0 como demo")
            detected_cameras.append(0)
    
    logger.info(f"Detección completada. Cámaras encontradas: {detected_cameras}")
    return detected_cameras

def _parse_resolution(resolution_str):
    """Parsear string de resolución"""
    if not resolution_str:
        return 640, 480  # Resolución por defecto
    
    try:
        parts = resolution_str.lower().split("x")
        if len(parts) == 2:
            width = int(parts[0])
            height = int(parts[1])
            return width, height
    except (ValueError, IndexError):
        logger.error(f"Error parseando resolución: {resolution_str}")
    
    return 640, 480  # Fallback

def _open_camera(index, resolution):
    """
    Abre una cámara con configuración específica
    """
    logger.info(f"Intentando abrir cámara índice {index} con resolución {resolution}")
    
    # Limpiar error anterior
    with camera_lock:
        camera_state["last_error"] = None
    
    width, height = _parse_resolution(resolution)
    logger.info(f"Resolución parseada: {width}x{height}")
    
    # Intentar con cada backend
    for backend in _BACKENDS:
        cap = _try_open_camera(index, backend, test_read=False)
        if cap:
            try:
                # Configurar resolución
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Verificar resolución actual
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = int(cap.get(cv2.CAP_PROP_FPS))
                
                logger.info(f"Configuración aplicada:")
                logger.info(f"  - Resolución: {width}x{height} → {actual_width}x{actual_height}")
                logger.info(f"  - FPS: 30 → {actual_fps}")
                
                # Probar leer un frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    logger.info(f"✅ Cámara {index} configurada exitosamente")
                    with camera_lock:
                        camera_state["initialization_success"] = True
                    return cap
                else:
                    logger.warning(f"Cámara {index} configurada pero no puede leer frames")
            
            except Exception as e:
                logger.error(f"Error configurando cámara {index}: {e}")
            
            cap.release()
    
    # Si llegamos aquí, falló la apertura
    error_msg = f"No se pudo abrir cámara índice {index} con ningún backend"
    logger.error(error_msg)
    with camera_lock:
        camera_state["last_error"] = error_msg
        camera_state["initialization_success"] = False
    
    return None

def camera_thread_func():
    """
    Función principal del hilo de captura de cámara
    """
    logger.info("🎥 Iniciando hilo de captura de cámara")
    
    last_idx = -1
    last_res = ""
    consecutive_failures = 0
    max_consecutive_failures = 30  # ~1 segundo a 30fps
    
    while True:
        try:
            with camera_lock:
                if not camera_state["is_running"]:
                    logger.info("🛑 Deteniendo hilo de cámara")
                    if camera_state["camera_object"]:
                        camera_state["camera_object"].release()
                        camera_state["camera_object"] = None
                    break
                
                current_idx = camera_state["camera_index"]
                current_res = camera_state["resolution"]
            
            # Reabrir cámara si cambió la configuración
            if current_idx != last_idx or current_res != last_res:
                logger.info(f"Cambio de configuración detectado: {current_idx}, {current_res}")
                
                # Cerrar cámara anterior
                with camera_lock:
                    if camera_state["camera_object"]:
                        camera_state["camera_object"].release()
                        camera_state["camera_object"] = None
                
                # Abrir nueva cámara
                if current_idx >= 0:
                    new_camera = _open_camera(current_idx, current_res)
                    with camera_lock:
                        camera_state["camera_object"] = new_camera
                
                last_idx = current_idx
                last_res = current_res
                consecutive_failures = 0
            
            # Capturar frame
            with camera_lock:
                cap = camera_state["camera_object"]
            
            if cap and cap.isOpened():
                try:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        with camera_lock:
                            camera_state["current_frame"] = frame.copy()
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.warning(f"Fallo leyendo frame (fallos consecutivos: {consecutive_failures})")
                        
                        with camera_lock:
                            camera_state["current_frame"] = None
                        
                        # Si hay muchos fallos consecutivos, intentar reabrir
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error("Demasiados fallos consecutivos, reabriendo cámara")
                            cap.release()
                            with camera_lock:
                                camera_state["camera_object"] = None
                            consecutive_failures = 0
                
                except Exception as e:
                    logger.error(f"Error capturando frame: {e}")
                    consecutive_failures += 1
                    with camera_lock:
                        camera_state["current_frame"] = None
            else:
                # No hay cámara o no está abierta
                with camera_lock:
                    camera_state["current_frame"] = None
        
        except Exception as e:
            logger.error(f"Error en hilo de cámara: {e}")
            time.sleep(0.1)  # Pausa en caso de error
            continue
        
        # Frame rate control
        time.sleep(1/30.0)  # ~30 FPS

def generate_frames():
    """
    Generador de frames para el stream MJPEG
    """
    logger.info("🎬 Iniciando generador de frames MJPEG")
    
    frame_count = 0
    
    while True:
        try:
            with camera_lock:
                if not camera_state["is_running"]:
                    logger.info("🛑 Deteniendo generador de frames")
                    break
                
                current_frame = camera_state["current_frame"]
                last_error = camera_state["last_error"]
            
            frame_count += 1
            
            # Crear frame de salida
            if current_frame is not None:
                # Frame real de la cámara
                output_frame = current_frame.copy()
                
                # Agregar información de debug (opcional)
                cv2.putText(output_frame, f"Frame: {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
            else:
                # Frame negro con mensaje de error
                output_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Agregar mensaje de error
                if last_error:
                    lines = [
                        "Error de camara:",
                        last_error[:50],  # Truncar mensaje largo
                        f"Frame: {frame_count}"
                    ]
                else:
                    lines = [
                        "Camara no configurada",
                        "Configure la camara primero",
                        f"Frame: {frame_count}"
                    ]
                
                for i, line in enumerate(lines):
                    y_pos = 150 + (i * 40)
                    cv2.putText(output_frame, line, (50, y_pos), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Codificar como JPEG
            ret, buffer = cv2.imencode('.jpg', output_frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + buffer.tobytes() + b'\r\n')
            else:
                logger.error("Error codificando frame como JPEG")
        
        except Exception as e:
            logger.error(f"Error en generador de frames: {e}")
            # Generar frame de error
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, f"Error: {str(e)[:30]}", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            ret, buffer = cv2.imencode('.jpg', error_frame)
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + buffer.tobytes() + b'\r\n')
        
        time.sleep(0.033)  # ~30 FPS

def get_camera_info():
    """
    Obtiene información del estado actual de la cámara
    """
    with camera_lock:
        return {
            "is_running": camera_state["is_running"],
            "camera_index": camera_state["camera_index"],
            "resolution": camera_state["resolution"],
            "has_camera_object": camera_state["camera_object"] is not None,
            "has_current_frame": camera_state["current_frame"] is not None,
            "last_error": camera_state["last_error"],
            "initialization_success": camera_state["initialization_success"]
        }

def start_camera_system():
    """
    Inicia el sistema de cámara (debe llamarse desde Flask)
    """
    with camera_lock:
        camera_state["is_running"] = True
    
    # El hilo se inicia desde core.py cuando se accede al dashboard
    logger.info("✅ Sistema de cámara habilitado")

def stop_camera_system():
    """
    Detiene el sistema de cámara
    """
    with camera_lock:
        camera_state["is_running"] = False
    
    logger.info("🛑 Sistema de cámara detenido")