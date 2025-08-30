import threading, time
from flask import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify, flash
from ..extensions import socketio
from ..services.camera import camera_state, camera_lock, detect_cameras, camera_thread_func, generate_frames
from ..services.analysis import analyze_faces_thread, get_temperature_valpo
from ..utils.authz import roles_required
from ..utils.db import guardar_configuracion_camara, guardar_configuracion_academica, agregar_metrica_grupal

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
                with camera_lock:
                    camera_state["camera_index"] = int(request.form["camera"])
                    camera_state["resolution"] = request.form["resolution"]
                session["camera_configured"] = True
                flash("Cámara configurada correctamente. 👍", "success")
                
                # Guardar la configuración de cámara en la base de datos
                guardar_configuracion_camara(session["user_id"], camera_state["camera_index"], camera_state["resolution"])

            except Exception as e:
                session["camera_configured"] = False
                flash(f"Error al guardar la configuración: {e} 👎", "danger")
            return redirect(url_for("core.config"))

        # Configuración académica
        elif "configurar_academica" in request.form:
            session['academic_config'] = {
                'nivel_ensenanza': request.form.get('nivel_ensenanza', ''),
                'grado': request.form.get('grado', ''),
                'materia': request.form.get('materia', ''),
                'temperatura': get_temperature_valpo()
            }
            session['academic_configured'] = True
            flash("Configuración académica guardada. 👍", "success")
            
            # Guardar la configuración académica en la base de datos
            guardar_configuracion_academica(session["user_id"], session['academic_config']['grado'], session['academic_config']['materia'])

            return redirect(url_for("core.config"))

    # Mostrar configuración actual
    return render_template("config.html",
        cameras=detect_cameras(),
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

    with camera_lock:
        camera_state["is_running"] = True

    # Iniciar el hilo de la cámara si no está en ejecución
    if camera_thread is None or not camera_thread.is_alive():
        camera_thread = threading.Thread(target=camera_thread_func, daemon=True)
        camera_thread.start()

    # Iniciar el hilo del análisis de emociones si no está en ejecución
    if analysis_thread is None or not analysis_thread.is_alive():
        analysis_thread = threading.Thread(target=analyze_faces_thread, args=(session.get('academic_config', {}),), daemon=True)
        analysis_thread.start()

    return render_template("dashboard_optimized.html", academic_config=session.get('academic_config', {}))


@bp_core.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp_core.route("/get_temperature")
def get_temperature_api():
    return jsonify({"temperature": get_temperature_valpo()})


# Eventos socket
@socketio.on("connect")
def handle_connect():
    print("🔌 Cliente conectado a Socket.IO")


@socketio.on("disconnect")
def handle_disconnect():
    print("🚫 Cliente desconectado de Socket.IO")

# Función para agregar métricas en tiempo real
def on_emotion_update(face_count, dominant_emotion, confidence, emotion_distribution, cognitive_load):
    # Guardar las métricas en la base de datos
    agregar_metrica_grupal(session["sid"], face_count, dominant_emotion, confidence, emotion_distribution, cognitive_load)
