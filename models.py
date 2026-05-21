from datetime import datetime, timezone
from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# UserMixin eklendi!
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User: {self.username}>"


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(150), nullable=False)
    teknolojiler = db.Column(db.String(250), nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(250), nullable=True)
    gorsel = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f"<Project: {self.baslik}>"


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Setting: {self.key}>"


class ChatLog(db.Model):
    """Bot konuşmalarını analitik amaçlı kaydeder — ham IP saklanmaz (KVKK)."""
    __tablename__ = 'chat_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    soru = db.Column(db.Text, nullable=False)
    cevap_ozet = db.Column(db.String(300))
    gorsel_turu = db.Column(db.String(50), index=True)
    dil = db.Column(db.String(5), default='tr', index=True)
    tarih = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    # utils.py'daki hash uzunluğuna (32) uyumlu hale getirildi!
    ip_parmak_izi = db.Column(db.String(32))

    def __repr__(self):
        return f"<ChatLog: {self.id} - {self.tarih.strftime('%Y-%m-%d')}>"