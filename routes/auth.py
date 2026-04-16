from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_user, logout_user, login_required
from extensions import limiter
from models import User
import secrets

auth_bp = Blueprint('auth', __name__)

def csrf_token_uret():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token

def csrf_dogrula():
    token = request.form.get("_csrf_token", "")
    session_token = session.get("_csrf_token", "")
    return token and session_token and secrets.compare_digest(token, session_token)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        if not csrf_dogrula():
            return render_template('login.html', error="Geçersiz istek. Sayfayı yenileyip tekrar deneyin.")
            
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            session['logged_in'] = True 
            return redirect(url_for('admin.admin_paneli'))
        else:
            return render_template('login.html', error="Hatalı giriş akhi!")
            
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400
    logout_user()
    session.clear()
    return redirect(url_for('public.home'))
