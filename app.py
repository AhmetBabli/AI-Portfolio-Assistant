import os
import logging

from flask import Flask, request, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

# Yeni konfigürasyon haritamızı içeri aktarıyoruz
from config import config_by_name
from extensions import db, login_manager, limiter


def create_app():
    app = Flask(__name__)
    
    # 1. Ortam seçimi (.env içinde FLASK_ENV yoksa varsayılan olarak 'development')
    env_name = os.getenv("FLASK_ENV", "development")
    config_cls = config_by_name[env_name]
    
    # Konfigürasyonu yükle
    app.config.from_object(config_cls)
    
    # Eğer production sınıfı ise özel güvenlik kontrollerini tetikle (Fail-Fast)
    if hasattr(config_cls, 'init_app'):
        config_cls.init_app(app)

    # ── Logging ───────────────────────────────────────────────────────────────
    # Flask logger'ın seviyesini konfigüre ediyoruz
    app.logger.setLevel(logging.INFO)
    if not app.debug:
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        for handler in app.logger.handlers:
            handler.setFormatter(formatter)

    # ── Uzantılar (Extensions) ────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    # Veritabanı tablolarının otomatik oluşturulmasını sağla (Canlı ortamda tablo yoksa hata vermemesi için)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning("Veritabanı tabloları oluşturulurken hata: %s", e)

    # Not: extensions.py içinde bunları zaten tanımlamıştık, 
    # burada kalması veya oradan yönetilmesi tamamen senin yoğurt yiyişine kalmış akhi.
    login_manager.login_view    = 'auth.login'
    login_manager.login_message = "Lütfen giriş yapın."

    # ── Gemini API — tek seferlik yapılandırma ────────────────────────────────
    api_key = app.config.get('GOOGLE_API_KEY')
    if api_key:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        app.logger.info(f"Gemini API başarıyla yapılandırıldı. Model: {app.config.get('GEMINI_MODEL')}")
    else:
        app.logger.warning("GOOGLE_API_KEY eksik — chat devre dışı kalacak.")

    # ── ProxyFix (Canlı ortamda gerçek kullanıcı IP'leri için) ────────────────
    if os.getenv("ENABLE_PROXY_FIX", "1") == "1":
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for    = int(os.getenv("PROXY_FIX_X_FOR",    "1")),
            x_proto  = int(os.getenv("PROXY_FIX_X_PROTO",  "1")),
            x_host   = int(os.getenv("PROXY_FIX_X_HOST",   "1")),
            x_port   = int(os.getenv("PROXY_FIX_X_PORT",   "0")),
            x_prefix = int(os.getenv("PROXY_FIX_X_PREFIX", "0")),
        )

    # ── Blueprint'ler ─────────────────────────────────────────────────────────
    from routes.public import public_bp
    from routes.auth   import auth_bp, csrf_token_uret
    from routes.admin  import admin_bp
    from routes.chat   import chat_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)

    # ── Context processor ─────────────────────────────────────────────────────
    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token_uret}

    # ── Güvenlik başlıkları (CSP & Security Headers) ──────────────────────────
    @app.after_request
    def guvenlik_basliklari(response):
        is_home = request.path == "/"
        csp_default = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none';"
        )
        csp_home = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: https:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https: wss:; "
            "frame-src 'self' https://prod.spline.design https://*.spline.design; "
            "worker-src 'self' blob:; "
            "child-src 'self' blob: https://prod.spline.design https://*.spline.design; "
            "media-src 'self' data: blob: https:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"]   = csp_home if is_home else csp_default
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        return response

    # ── Error handler'lar ─────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template('429.html'), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error("500 Hatası: %s", e, exc_info=True)
        return render_template('500.html'), 500

    return app


# Global alandaki app = create_app() kaldırıldı. 
# Artık projenin ana giriş noktası tamamen modüler.

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=app.config.get("DEBUG", False))