import json
import re
from datetime import datetime, timezone

import google.generativeai as genai
from flask import Blueprint, request, jsonify, current_app, session

from extensions import limiter, db
from prompts import get_bot_prompt
from models import Setting, ChatLog
from utils import get_settings, get_projects_text, sanitize_input, ip_hash

chat_bp = Blueprint('chat', __name__)

# ── Gemini model instance — modül seviyesinde tekrar kullanılır ────────────
_gemini_model = None


def _get_model():
    """Gemini model nesnesini lazy-init ile döner (her istekte yeniden oluşturmaz)."""
    global _gemini_model
    if _gemini_model is None:
        model_name = current_app.config.get('GEMINI_MODEL', 'gemini-1.5-flash')
        _gemini_model = genai.GenerativeModel(
            model_name,
            generation_config={"response_mime_type": "application/json"},
        )
    return _gemini_model


class ConversationContext:
    """Session-based conversation history with token-aware pruning."""

    def __init__(self, messages=None, max_tokens: int = 800):
        self.messages = list(messages or [])
        self.max_tokens = max_tokens

    def _token_count(self, text: str) -> int:
        return len(str(text).split())

    def total_tokens(self) -> int:
        return sum(self._token_count(m['text']) for m in self.messages)

    def _prune(self):
        while len(self.messages) > 16 or self.total_tokens() > self.max_tokens:
            self.messages.pop(0)

    def add(self, role: str, text: str):
        self.messages.append({'role': role, 'text': text})
        self._prune()

    def get_history_text(self) -> str:
        return "\n".join(f"{m['role']}: {m['text']}" for m in self.messages)

    def to_dict_list(self):
        return [dict(role=m['role'], text=m['text']) for m in self.messages]


class IntentDetector:
    INTENT_MAP = {
        'interview': [
            'mülakat', 'kendini anlat', 'about yourself', 'who are you',
            'kendinden', 'kimdir', 'hakkında', 'kendini tanıt'
        ],
        'project': [
            'proje', 'yaptığın iş', 'hangi projeler', 'portfolio', 'projeler',
            'çalışma', 'uygulama'
        ],
        'contact': [
            'iletişim', 'contact', 'e-posta', 'email', 'telefon', 'linkedin',
            'nasıl ulaşırım'
        ],
        'technical': [
            'teknik', 'nasıl çalışır', 'mimari', 'api', 'backend', 'frontend',
            'veritabanı', 'database', 'flask', 'python'
        ],
        'social': [
            'merhaba', 'selam', 'nasılsın', 'teşekkür', 'sağ ol', 'günaydın',
            'iyi günler', 'iyi akşamlar'
        ],
    }

    @classmethod
    def detect(cls, text: str) -> str:
        lower = (text or '').lower()
        for intent, keywords in cls.INTENT_MAP.items():
            if any(keyword in lower for keyword in keywords):
                return intent
        return 'general'


class SentimentAnalyzer:
    POSITIVE_WORDS = ['teşekkür', 'harika', 'mükemmel', 'güzel', 'iyi', 'memnun', 'şanslı', 'mutlu']
    NEGATIVE_WORDS = ['kötü', 'problem', 'hata', 'şikayet', 'üzgün', 'sinir', 'kırgın', 'değil']

    @classmethod
    def analyze(cls, text: str) -> str:
        lower = (text or '').lower()
        positive = sum(1 for word in cls.POSITIVE_WORDS if word in lower)
        negative = sum(1 for word in cls.NEGATIVE_WORDS if word in lower)
        if positive > negative + 1:
            return 'positive'
        if negative > positive + 1:
            return 'negative'
        return 'neutral'


@chat_bp.route('/chat', methods=['POST'])
@limiter.limit("20 per minute")
def chat():
    # --- İstek doğrulama ---
    if not request.is_json:
        return jsonify({'response': 'Geçersiz istek formatı.', 'gorsel': 'error'}), 400

    payload = request.get_json(silent=True) or {}
    user_msg = str(payload.get('message', '')).strip()
    language = str(payload.get('language', 'tr')).strip().lower()

    if len(user_msg) > 1000:
        return jsonify({'response': 'Mesaj çok uzun. Lütfen kısaltın.', 'gorsel': 'error'}), 400
    if not user_msg:
        return jsonify({'response': '...', 'gorsel': 'idle'})

    user_msg = sanitize_input(user_msg)

    # --- Analitik: toplam mesaj sayacı ---
    try:
        msg_s = Setting.query.filter_by(key="toplam_mesaj").first()
        if not msg_s:
            msg_s = Setting(key="toplam_mesaj", value="0")
            db.session.add(msg_s)
            db.session.flush()
        # Atomic update via raw SQL (race-condition safe)
        db.session.execute(
            db.text(
                "UPDATE setting SET value = CAST(value AS INTEGER) + 1 "
                "WHERE id = :sid"
            ),
            {"sid": msg_s.id},
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.warning("Mesaj sayacı güncellenemedi: %s", e)
        db.session.rollback()

    # --- Niyet ve Duygu Analizi ---
    intent = IntentDetector.detect(user_msg)
    sentiment = SentimentAnalyzer.analyze(user_msg)

    # --- Konuşma geçmişi (session) ---
    ctx = ConversationContext(messages=session.get('chat_history', []))
    history_text = ctx.get_history_text()

    # --- Veritabanından bağlam (cache destekli) ---
    cv_data = get_settings(use_cache=True)
    proje_metni = get_projects_text()

    full_prompt = get_bot_prompt(
        cv_data=cv_data, 
        proje_metni=proje_metni, 
        language=language, 
        user_msg=user_msg, 
        intent=intent, 
        sentiment=sentiment, 
        history_text=history_text
    )

    try:
        # genai.configure() → app.py'de bir kez yapılıyor; burada tekrar çağrılmıyor
        model = _get_model()
        response = model.generate_content(full_prompt)

        # --- JSON parse (fallback ile) ---
        try:
            data = json.loads(response.text)
        except (json.JSONDecodeError, ValueError):
            current_app.logger.warning("Gemini JSON parse hatası, fallback aktif. Raw: %s", response.text[:200])
            # Metni doğrudan cevap olarak kullan
            cleaned = re.sub(r'```json\s*|```', '', response.text).strip()
            try:
                data = json.loads(cleaned)
            except (json.JSONDecodeError, ValueError):
                data = {'cevap': response.text, 'gorsel': 'idle'}

        bot_cevap = data.get('cevap', '')
        gorsel_turu = data.get('gorsel', 'idle')

        # --- ChatLog kaydet ---
        try:
            log = ChatLog(
                soru=user_msg[:500],
                cevap_ozet=(bot_cevap or '')[:300],
                gorsel_turu=gorsel_turu,
                dil=language,
                ip_parmak_izi=ip_hash(request.remote_addr or ''),
                tarih=datetime.now(timezone.utc),
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            current_app.logger.warning("ChatLog kaydedilemedi: %s", e)
            db.session.rollback()

        # --- Hafıza güncelle ---
        ctx.add("Ziyaretçi", user_msg)
        ctx.add("Sırdaş", bot_cevap)
        session['chat_history'] = ctx.to_dict_list()
        session.modified = True

        return jsonify({'response': bot_cevap, 'gorsel': gorsel_turu})

    except Exception as e:
        error_str = str(e)
        current_app.logger.error("CHAT HATASI [%s]: %s", type(e).__name__, error_str, exc_info=True)

        # --- 429 Rate Limit / Quota Exceeded ---
        if '429' in error_str or 'ResourceExhausted' in error_str or 'quota' in error_str.lower():
            rate_msg = (
                "Çok fazla istek gönderildi, lütfen biraz bekleyip tekrar deneyin. ⏳"
                if language == 'tr'
                else "Too many requests. Please wait a moment and try again. ⏳"
            )
            return jsonify({'response': rate_msg, 'gorsel': 'idle'})
        
        # --- API Key hatası ---
        if 'API key' in error_str or 'authentication' in error_str.lower() or 'unauthorized' in error_str.lower():
            err = ("API anahtarı sorunu. Admin kontrol etsin." if language == 'tr' 
                   else "API key issue. Please contact admin.")
            current_app.logger.critical("⚠️ API KEY HATASI: %s", error_str)
            return jsonify({'response': err, 'gorsel': 'error'})

        err = "Sistem hatası. Lütfen tekrar deneyin." if language == 'tr' else "System error. Please try again."
        return jsonify({'response': err, 'gorsel': 'error'})
