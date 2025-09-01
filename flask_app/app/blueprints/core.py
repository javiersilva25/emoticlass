import threading, time
from flask import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify, flash
from ..extensions import socketio
from ..services.camera import (
    camera_state, camera_lock, detect_cameras, camera_thread_func,
    generate_frames, get_camera_info, start_camera_system
)
from ..services.analysis import analyze_faces_thread, get_temperature_valpo
from ..utils.authz import roles_required
from ..utils.db import (
    guardar_configuracion_camara, guardar_configuracion_academica, agregar_metrica_grupal,
    crear_profesor, listar_profesores, obtener_profesor_por_usuario,
    crear_curso, listar_cursos, listar_cursos_por_profesor,
    asignar_profesor_a_curso, eliminar_curso
)
import traceback
import cv2
import numpy as np

bp_core = Blueprint("core", __name__)

camera_thread = None
analysis_thread = None

# ========================
# Configuración
# ========================
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

                info = get_camera_info()
                print(f"📊 Estado después de configurar: {info}")

                session["camera_configured"] = True
                flash("Cámara configurada correctamente. 👍", "success")

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

                guardar_configuracion_academica(session["user_id"],
                                              session['academic_config']['grado'],
                                              session['academic_config']['materia'])

            except Exception as e:
                print(f"❌ Error en configuración académica: {e}")
                flash(f"Error al guardar la configuración académica: {e} 👎", "danger")

            return redirect(url_for("core.config"))

    try:
        cameras_detected = detect_cameras()
        print(f"📷 Cámaras detectadas: {cameras_detected}")
    except Exception as e:
        print(f"❌ Error detectando cámaras: {e}")
        cameras_detected = [0]

    return render_template("config.html",
        cameras=cameras_detected,
        resolutions=["640x480", "1280x720", "1920x1080"],
        temperatura=get_temperature_valpo(),
        academic_config=session.get('academic_config', {}),
        camera_configured=session.get('camera_configured', False),
        academic_configured=session.get('academic_configured', False)
    )

# ========================
# Dashboard
# ========================
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

    start_camera_system()

    with camera_lock:
        camera_state["is_running"] = True

    info = get_camera_info()
    print(f"📊 Estado de cámara en dashboard: {info}")

    if camera_thread is None or not camera_thread.is_alive():
        print("🎥 Iniciando hilo de cámara")
        camera_thread = threading.Thread(target=camera_thread_func, daemon=True, name="CameraThread")
        camera_thread.start()
        time.sleep(1)

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

# ========================
# Video y APIs de cámara
# ========================
@bp_core.route("/video_feed")
def video_feed():
    try:
        print("📹 Solicitando video feed")
        info = get_camera_info()
        print(f"📊 Estado de cámara para video feed: {info}")

        if not info["is_running"]:
            with camera_lock:
                camera_state["is_running"] = True

        return Response(generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

    except Exception as e:
        print(f"❌ Error en video feed: {e}")
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
        return jsonify({"temperature": 15.0, "error": str(e)})

@bp_core.route("/api/camera/info")
def camera_info_api():
    try:
        info = get_camera_info()
        return jsonify({"success": True, "info": info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp_core.route("/api/camera/test")
def camera_test_api():
    try:
        cameras = detect_cameras()
        info = get_camera_info()
        return jsonify({"success": True, "cameras_detected": cameras, "camera_info": info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========================
# SocketIO
# ========================
@socketio.on("connect")
def handle_connect():
    print("🔌 Cliente conectado a Socket.IO")

@socketio.on("disconnect")
def handle_disconnect():
    print("🚫 Cliente desconectado de Socket.IO")

@socketio.on("get_camera_info")
def handle_get_camera_info():
    try:
        info = get_camera_info()
        socketio.emit("camera_info_response", {"success": True, "info": info})
    except Exception as e:
        socketio.emit("camera_info_response", {"success": False, "error": str(e)})

# ========================
# Métricas
# ========================
def on_emotion_update(face_count, dominant_emotion, confidence, emotion_distribution, cognitive_load):
    try:
        agregar_metrica_grupal(session.get("sid", "unknown"), face_count,
                             dominant_emotion, confidence, emotion_distribution, cognitive_load)
    except Exception as e:
        print(f"Error guardando métricas: {e}")

# ========================
# Debug endpoints
# ========================
@bp_core.route("/debug/camera")
def debug_camera():
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
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

# ========================
# Profesores
# ========================
@bp_core.route("/api/profesores", methods=["GET"])
@roles_required("admin")
def api_listar_profesores():
    return jsonify({"success": True, "data": listar_profesores()})

@bp_core.route("/api/profesores", methods=["POST"])
@roles_required("admin")
def api_crear_profesor():
    data = request.json or {}
    usuario_id = data.get("usuario_id")
    titulo = data.get("titulo")
    especialidad = data.get("especialidad")
    ok, msg = crear_profesor(usuario_id, titulo, especialidad)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)

@bp_core.route("/api/profesores/<int:usuario_id>", methods=["GET"])
@roles_required("admin","profesor")
def api_obtener_profesor(usuario_id):
    prof = obtener_profesor_por_usuario(usuario_id)
    if prof:
        return jsonify({"success": True, "data": prof})
    return jsonify({"success": False, "error": "No encontrado"}), 404

# ========================
# Cursos
# ========================
@bp_core.route("/api/cursos", methods=["GET"])
@roles_required("admin","profesor")
def api_listar_cursos():
    return jsonify({"success": True, "data": listar_cursos()})

@bp_core.route("/api/cursos", methods=["POST"])
@roles_required("admin")
def api_crear_curso():
    data = request.json or {}
    nombre = data.get("nombre")
    grado_id = data.get("grado_id")
    asignatura_id = data.get("asignatura_id")
    profesor_id = data.get("profesor_id")
    ok, msg = crear_curso(nombre, grado_id, asignatura_id, profesor_id)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)

@bp_core.route("/api/cursos/profesor/<int:profesor_id>", methods=["GET"])
@roles_required("admin","profesor")
def api_listar_cursos_por_profesor(profesor_id):
    return jsonify({"success": True, "data": listar_cursos_por_profesor(profesor_id)})

@bp_core.route("/api/cursos/<int:curso_id>/asignar/<int:profesor_id>", methods=["PUT"])
@roles_required("admin")
def api_asignar_profesor(curso_id, profesor_id):
    ok, msg = asignar_profesor_a_curso(curso_id, profesor_id)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)

@bp_core.route("/api/cursos/<int:curso_id>", methods=["DELETE"])
@roles_required("admin")
def api_eliminar_curso(curso_id):
    if eliminar_curso(curso_id):
        return jsonify({"success": True, "message": "Curso eliminado"})
    return jsonify({"success": False, "error": "No encontrado"}), 404
