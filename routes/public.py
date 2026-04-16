from flask import Blueprint, render_template, session
from models import Setting
from extensions import db

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def home():
    if not session.get('visited_recently'):
        setting = Setting.query.filter_by(key="sayfa_goruntulenme").first()
        if not setting:
            setting = Setting(key="sayfa_goruntulenme", value="0")
            db.session.add(setting)
            
        current_val = 0
        try:
            current_val = int(setting.value or 0)
        except:
            pass
            
        setting.value = str(current_val + 1)
        db.session.commit()
        session['visited_recently'] = True
        
    return render_template('index.html')
