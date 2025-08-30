import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave_secreta_analisis_emociones_2025")
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    CSV_DIR = os.getenv("CSV_DIR", "emociones")
    DEBUG = False
    HOST = "0.0.0.0"
    PORT = 5001
