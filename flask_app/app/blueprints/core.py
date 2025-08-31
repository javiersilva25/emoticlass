import threading, time
from flask import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify, flash
from ..extensions import socketio
from ..services.camera import (
    camera_state, camera_lock, detect_cameras, camera_thread_func, 
    generate_frames, get_camera_info, start_camera_system
)
from ..services.analysis import analyze_faces_thread, get_temperature_valpo
from ..utils.authz import roles_required
from ..utils.db import guardar_configuracion_camara, guardar_configuracion_academica, agregar_metrica_grupal
import traceback
import cv2
import numpy as np

bp_core = Blueprint("core", __name__)

camera_thread = None
analysis_thread = None

@bp_core.route("/config", methods=["GET", "POST"])
@roles_required("admin", "profesor")
def config():
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # Configuración de cámara
        if "configurar_camara" in request.form:
            try:
                camera_index = int(request.form["camera"])
                resolution = request.form["resolution"]
                
                print(f"🎥 Configurando cámara: índice={camera_index}, resolución={resolution}")
                
                with camera_lock:
                    camera_state["camera_index"] = camera_index
                    camera_state["resolution"] = resolution
                    # No iniciamos is_running aquí, solo configuramos
                
                # Verificar que la configuración se guardó
                info = get_camera_info()
                print(f"📊 Estado después de configurar: {info}")
                
                session["camera_configured"] = True
                flash("Cámara configurada correctamente. 👍", "success")
                
                # Guardar la configuración de cámara en la base de datos
                guardar_configuracion_camara(session["user_id"], camera_index, resolution)

            except Exception as e:
                print(f"❌ Error configurando cámara: {e}")
                session["camera_configured"] = False
                flash(f"Error al configurar la cámara: {e} 👎", "danger")
            return redirect(url_for("core.config"))

        # Configuración académica
        elif "configurar_academica" in request.form:
            try:
                session['academic_config'] = {
                    'nivel_ensenanza': request.form.get('nivel_ensenanza', ''),
                    'grado': request.form.get('grado', ''),
                    'materia': request.form.get('materia', ''),
                    'temperatura': get_temperature_valpo()
                }
                session['academic_configured'] = True
                flash("Configuración académica guardada. 👍", "success")
                
                # Guardar la configuración académica en la base de datos
                guardar_configuracion_academica(session["user_id"], 
                                              session['academic_config']['grado'], 
                                              session['academic_config']['materia'])

            except Exception as e:
                print(f"❌ Error en configuración académica: {e}")
                flash(f"Error al guardar la configuración académica: {e} 👎", "danger")
            
            return redirect(url_for("core.config"))

    # GET request - mostrar página de configuración
    try:
        cameras_detected = detect_cameras()
        print(f"📷 Cámaras detectadas: {cameras_detected}")
    except Exception as e:
        print(f"❌ Error detectando cámaras: {e}")
        cameras_detected = [0]  # Fallback
    
    return render_template("config.html",
        cameras=cameras_detected,
        resolutions=["640x480", "1280x720", "1920x1080"],
        temperatura=get_temperature_valpo(),
        academic_config=session.get('academic_config', {}),
        camera_configured=session.get('camera_configured', False),
        academic_configured=session.get('academic_configured', False)
    )


@bp_core.route("/dashboard")
@roles_required("admin", "profesor")
def dashboard():
    global camera_thread, analysis_thread
    
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))

    if not session.get("camera_configured") or not session.get("academic_configured"):
        flash("Debe configurar la cámara y los datos académicos primero.", "warning")
        return redirect(url_for("core.config"))

    print("🚀 Accediendo al dashboard - iniciando sistema de cámara")
    
    # Iniciar sistema de cámara
    start_camera_system()
    
    with camera_lock:
        camera_state["is_running"] = True
    
    # Verificar estado de la cámara
    info = get_camera_info()
    print(f"📊 Estado de cámara en dashboard: {info}")

    # Iniciar el hilo de la cámara si no está en ejecución
    if camera_thread is None or not camera_thread.is_alive():
        print("🎥 Iniciando hilo de cámara")
        camera_thread = threading.Thread(target=camera_thread_func, daemon=True, name="CameraThread")
        camera_thread.start()
        # Dar tiempo para que se inicialice
        time.sleep(1)
    
    # Iniciar el hilo del análisis de emociones si no está en ejecución
    if analysis_thread is None or not analysis_thread.is_alive():
        print("🧠 Iniciando hilo de análisis de emociones")
        analysis_thread = threading.Thread(
            target=analyze_faces_thread, 
            args=(session.get('academic_config', {}),), 
            daemon=True, 
            name="AnalysisThread"
        )
        analysis_thread.start()

    return render_template("dashboard_optimized.html", 
                         academic_config=session.get('academic_config', {}))


@bp_core.route("/video_feed")
def video_feed():
    """Endpoint para el stream de video"""
    try:
        print("📹 Solicitando video feed")
        
        # Verificar que la cámara está configurada
        info = get_camera_info()
        print(f"📊 Estado de cámara para video feed: {info}")
        
        if not info["is_running"]:
            print("⚠️ Cámara no está corriendo, iniciando...")
            with camera_lock:
                camera_state["is_running"] = True
        
        return Response(generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    except Exception as e:
        print(f"❌ Error en video feed: {e}")
        # Retornar un frame de error
        import numpy as np
        import cv2
        
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, f"Error: {str(e)}", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        def error_generator():
            ret, buffer = cv2.imencode('.jpg', error_frame)
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + buffer.tobytes() + b'\r\n')
        
        return Response(error_generator(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')


@bp_core.route("/get_temperature")
def get_temperature_api():
    try:
        temp = get_temperature_valpo()
        return jsonify({"temperature": temp})
    except Exception as e:
        print(f"❌ Error obteniendo temperatura: {e}")
        return jsonify({"temperature": 15.0, "error": str(e)})


@bp_core.route("/api/camera/info")
def camera_info_api():
    """API para obtener información de la cámara"""
    try:
        info = get_camera_info()
        return jsonify({
            "success": True,
            "info": info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp_core.route("/api/camera/test")
def camera_test_api():
    """API para probar la configuración de cámara"""
    try:
        # Forzar detección de cámaras
        cameras = detect_cameras()
        info = get_camera_info()
        
        return jsonify({
            "success": True,
            "cameras_detected": cameras,
            "camera_info": info
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Eventos socket
@socketio.on("connect")
def handle_connect():
    print("🔌 Cliente conectado a Socket.IO")


@socketio.on("disconnect")
def handle_disconnect():
    print("🚫 Cliente desconectado de Socket.IO")


@socketio.on("get_camera_info")
def handle_get_camera_info():
    """Manejar solicitud de información de cámara via WebSocket"""
    try:
        info = get_camera_info()
        socketio.emit("camera_info_response", {
            "success": True,
            "info": info
        })
    except Exception as e:
        socketio.emit("camera_info_response", {
            "success": False,
            "error": str(e)
        })


# Función para agregar métricas en tiempo real
def on_emotion_update(face_count, dominant_emotion, confidence, emotion_distribution, cognitive_load):
    # Guardar las métricas en la base de datos
    try:
        agregar_metrica_grupal(session.get("sid", "unknown"), face_count, 
                             dominant_emotion, confidence, emotion_distribution, cognitive_load)
    except Exception as e:
        print(f"Error guardando métricas: {e}")

# Agrega estos endpoints temporalmente a tu core.py para debugging

@bp_core.route("/debug/camera")
def debug_camera():
    """Endpoint de debug para cámara"""
    try:
        info = get_camera_info()
        cameras = detect_cameras()
        
        return jsonify({
            "cameras_detected": cameras,
            "camera_state": info,
            "session_camera_configured": session.get('camera_configured', False),
            "session_academic_configured": session.get('academic_configured', False),
            "session_academic_config": session.get('academic_config', {}),
            "user_logged_in": session.get('logged_in', False),
            "thread_info": {
                "camera_thread_alive": camera_thread.is_alive() if camera_thread else False,
                "analysis_thread_alive": analysis_thread.is_alive() if analysis_thread else False
            }
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@bp_core.route("/debug/camera/force-start")
def debug_force_start_camera():
    """Forzar inicio de cámara para debug"""
    global camera_thread
    
    try:
        print("🔧 [DEBUG] Forzando inicio de cámara...")
        
        # Configurar cámara con valores por defecto
        with camera_lock:
            camera_state["camera_index"] = 0
            camera_state["resolution"] = "640x480"
            camera_state["is_running"] = True
        
        # Iniciar hilo si no existe
        if camera_thread is None or not camera_thread.is_alive():
            print("🔧 [DEBUG] Iniciando nuevo hilo de cámara...")
            camera_thread = threading.Thread(target=camera_thread_func, daemon=True, name="DebugCameraThread")
            camera_thread.start()
            time.sleep(2)  # Dar tiempo para inicializar
        
        # Verificar estado
        info = get_camera_info()
        print(f"🔧 [DEBUG] Estado después de forzar inicio: {info}")
        
        return jsonify({
            "success": True,
            "message": "Cámara forzada a iniciar",
            "camera_info": info,
            "thread_alive": camera_thread.is_alive() if camera_thread else False
        })
        
    except Exception as e:
        print(f"🔧 [DEBUG] Error forzando inicio: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bp_core.route("/debug/camera/test-frame")
def debug_test_frame():
    """Probar captura de un frame individual"""
    try:
        print("🔧 [DEBUG] Probando captura de frame individual...")
        
        # Intentar abrir cámara directamente
        cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
        if not cap.isOpened():
            return jsonify({
                "success": False,
                "error": "No se pudo abrir cámara directamente"
            })
        
        # Configurar
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Leer frame
        ret, frame = cap.read()
        cap.release()
        
        if ret and frame is not None:
            return jsonify({
                "success": True,
                "message": "Frame capturado exitosamente",
                "frame_shape": frame.shape,
                "frame_type": str(frame.dtype)
            })
        else:
            return jsonify({
                "success": False,
                "error": "No se pudo leer frame"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bp_core.route("/debug/video-test")
def debug_video_test():
    """Stream de video de prueba simple"""
    def generate_test_frames():
        print("🔧 [DEBUG] Generando frames de prueba...")
        
        for i in range(100):  # 100 frames de prueba
            # Crear frame de prueba
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Agregar texto
            cv2.putText(test_frame, f"TEST FRAME {i}", (200, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(test_frame, f"Time: {time.time():.2f}", (200, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Codificar
            ret, buffer = cv2.imencode('.jpg', test_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + buffer.tobytes() + b'\r\n')
            
            time.sleep(0.1)  # 10 FPS
    
    return Response(generate_test_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')