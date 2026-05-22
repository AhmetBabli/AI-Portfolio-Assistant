import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

class Config:
    """Taban Konfigürasyon Sınıfı. Ortak ayarlar burada yer alır."""
    
    # ── Güvenlik ve Oturum ────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # ── Veritabanı Taban Ayarı ────────────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Rate Limiting & API ───────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    
    # LLM Modelini konfigürasyona bağladık
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ── Dosya Yolları ─────────────────────────────────────────────────────────
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')


class DevelopmentConfig(Config):
    """Geliştirme (Local) Ortamı Ayarları"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(BASE_DIR, 'sirdas_dev.db')}"
    )
    # Lokal çalışırken HTTPS zorunluluğunu kaldırıyoruz
    SESSION_COOKIE_SECURE = False
    
    # Lokal için anahtar yoksa geçici üretilebilir (Tek worker çalıştığı için güvenli)
    if not Config.SECRET_KEY:
        Config.SECRET_KEY = "dev-secret-key-sirdas-ai"


class ProductionConfig(Config):
    """Canlı (Production) Ortam Ayarları"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")  # Canlıda PostgreSQL/MySQL URL'i zorunlu olsun
    SESSION_COOKIE_SECURE = True  # Canlıda mutlaka HTTPS kullanılmalı

    @classmethod
    def init_app(cls, app):
        # Canlı ortamda kritik anahtarlar eksikse uygulamayı KESİNLİKLE başlatma (Fail-Fast)
        if not cls.SECRET_KEY:
            raise ValueError(
                "❌ CANLI ORTAM HATASI: FLASK_SECRET_KEY tanımlı değil! "
                "Çoklu worker yapısında oturum düşmelerini engellemek için sabit bir key zorunludur."
            )
        if not cls.GOOGLE_API_KEY:
            raise ValueError("❌ CANLI ORTAM HATASI: GOOGLE_API_KEY veya GEMINI_API_KEY bulunamadı!")


# Uygulama başlatılırken FLASK_ENV'ye göre seçilmesi için sözlük yapısı
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}