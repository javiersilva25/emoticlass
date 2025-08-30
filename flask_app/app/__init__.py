from flask import Flask
from .config import Config
from .extensions import socketio
from .utils.db import init_db, init_db_dominio
from .blueprints.auth import bp_auth
from .blueprints.core import bp_core

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    # SocketIO
    socketio.init_app(app, cors_allowed_origins=app.config["SOCKETIO_CORS_ALLOWED_ORIGINS"])

    # Inicialización de la base de datos
    init_db()          # usuarios
    init_db_dominio()  # configuraciones, sesiones, métricas

    # Blueprints
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_core)

    @app.route("/healthz")
    def healthz():
        return "ok"

    return app
