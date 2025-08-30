from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    print("===================================================================")
    print("🚀 Sistema de Análisis de Emociones (Arquitectura Robusta)")
    print("===================================================================")
    print("🌐 Acceso: http://127.0.0.1:5001")
    socketio.run(app, host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"], allow_unsafe_werkzeug=True)
