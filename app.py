import os
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db, login_manager, limiter
import google.generativeai as genai

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Lütfen giriş yapın."

    # Proxy Fix
    proxy_fix_enabled = os.getenv("ENABLE_PROXY_FIX", "1") == "1"
    if proxy_fix_enabled:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=int(os.getenv("PROXY_FIX_X_FOR", "1")),
            x_proto=int(os.getenv("PROXY_FIX_X_PROTO", "1")),
            x_host=int(os.getenv("PROXY_FIX_X_HOST", "1")),
            x_port=int(os.getenv("PROXY_FIX_X_PORT", "0")),
            x_prefix=int(os.getenv("PROXY_FIX_X_PREFIX", "0")),
        )

    # Blueprints
    from routes.public import public_bp
    from routes.auth import auth_bp, csrf_token_uret
    from routes.admin import admin_bp
    from routes.chat import chat_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token_uret}

    @app.after_request
    def guvenlik_basliklari(response):
        is_home = request.path == "/"
        csp_default = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
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
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
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
        response.headers["Content-Security-Policy"] = csp_home if is_home else csp_default
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
        
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")