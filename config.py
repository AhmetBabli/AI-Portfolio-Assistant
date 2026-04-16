import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mevcut yapıyı koruyarak dotenv yüklemesi
legacy_env_path = os.path.join(BASE_DIR, ".env", ".env")
load_dotenv(legacy_env_path)
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", os.urandom(32).hex())
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'sirdas.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB limit
    
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')
