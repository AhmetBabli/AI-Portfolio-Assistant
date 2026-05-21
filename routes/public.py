import time

from flask import Blueprint, render_template, session, current_app
from models import Setting
from extensions import db

public_bp = Blueprint('public', __name__)

# Ziyaret sayacı — 24 saat TTL
_VISIT_TTL_SECONDS = 86400  # 24 saat


@public_bp.route('/')
def home():
    last_visit = session.get('last_visit_ts', 0)
    now = time.time()

    if (now - last_visit) > _VISIT_TTL_SECONDS:
        try:
            setting = Setting.query.filter_by(key="sayfa_goruntulenme").first()
            if not setting:
                setting = Setting(key="sayfa_goruntulenme", value="0")
                db.session.add(setting)

            try:
                current_val = int(setting.value or 0)
            except (ValueError, TypeError):
                current_val = 0

            setting.value = str(current_val + 1)
            db.session.commit()
            session['last_visit_ts'] = now
        except Exception as e:
            current_app.logger.warning("Ziyaret sayacı güncellenemedi: %s", e)
            db.session.rollback()

    return render_template('index.html')
