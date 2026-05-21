from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Eklentilerin tanımlanması
db = SQLAlchemy()
login_manager = LoginManager()

# --- FLASK-LOGIN AYARLARI ---
# Giriş yapmamış kullanıcı yetki isteyen bir sayfaya girerse buraya yönlendirilir.
# NOT: Kendi projedeki login endpoint'inin adını yazmalısın (örn: 'auth.login')
login_manager.login_view = 'login' 
# Yönlendirme sırasında gösterilecek mesaj (Flash message)
login_manager.login_message = 'Lütfen bu sayfayı görüntülemek için giriş yapın.'
login_manager.login_message_category = 'warning'


# --- FLASK-LIMITER AYARLARI ---
limiter = Limiter(
    key_func=get_remote_address,
    # Tüm rotalar için varsayılan bir taban koruma sınırı belirleyebilirsin
    default_limits=["200 per day", "50 per hour"],
    
    # İleride Gunicorn ve çoklu worker ile canlıya çıkarken bu satırı aktif edip 
    # bellek yönetimini Redis'e devretmelisin:
    # storage_uri="redis://localhost:6379" 
)