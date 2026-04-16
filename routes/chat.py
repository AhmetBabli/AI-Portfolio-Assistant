import json
import google.generativeai as genai
from flask import Blueprint, request, jsonify, current_app, session
from extensions import limiter, db
from prompts import get_bot_prompt
from models import Project, Setting

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
@limiter.limit("20 per minute")
def chat():
    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        return jsonify({'response': "Sistem: API Anahtarı eksik.", 'gorsel': 'idle'})

    if not request.is_json:
        return jsonify({'response': 'Geçersiz istek formatı.', 'gorsel': 'error'}), 400

    payload = request.get_json(silent=True) or {}
    user_msg = str(payload.get('message', '')).strip()
    language = str(payload.get('language', 'tr')).strip().lower()

    if len(user_msg) > 1000:
        return jsonify({'response': 'Mesaj çok uzun. Lütfen kısaltın.', 'gorsel': 'error'}), 400

    if not user_msg:
        return jsonify({'response': '...', 'gorsel': 'idle'})

    # Mesaj sayısını artırma (Analytics)
    msg_setting = Setting.query.filter_by(key="toplam_mesaj").first()
    if not msg_setting:
        msg_setting = Setting(key="toplam_mesaj", value="0")
        db.session.add(msg_setting)
    try:
        msg_setting.value = str(int(msg_setting.value or 0) + 1)
        db.session.commit()
    except Exception:
        pass

    # Hafıza Okuma (Session)
    if 'chat_history' not in session:
        session['chat_history'] = []
        
    history = session['chat_history']
    history_text = "\n".join([f"{m['role']}: {m['text']}" for m in history[-6:]])

    settings_obj = Setting.query.all()
    cv_data = {s.key: s.value for s in settings_obj}
    projeler = Project.query.all()
    proje_metni = "\n".join([f"- {p.baslik} ({p.teknolojiler}): {p.aciklama}" for p in projeler])

    full_prompt = get_bot_prompt(cv_data, proje_metni, language, user_msg, history_text)
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(full_prompt)
        data = json.loads(response.text)
        
        # Hafıza Kaydetme
        history.append({"role": "Ziyaretçi", "text": user_msg})
        history.append({"role": "Sırdaş", "text": data.get('cevap', '')})
        session['chat_history'] = history[-8:] # Son 8 mesajı tutalım (4 soru 4 cevap)
        session.modified = True
        
        return jsonify({'response': data.get('cevap', ''), 'gorsel': data.get('gorsel', 'idle')})
        
    except Exception as e:
        print(f"🔴 CHAT HATASI: {e}")
        error_msg = "Sistem hatası. Lütfen tekrar deneyin." if language == 'tr' else "System error. Please try again."
        return jsonify({'response': error_msg, 'gorsel': 'error'})
