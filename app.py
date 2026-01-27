import json
import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

app = Flask(__name__)

# --- ADIM 1: DİNAMİK VERİ YÖNETİMİ ---
def projeleri_yukle():
    """static/projects.json dosyasından projeleri okur."""
    try:
        json_path = os.path.join('static', 'projects.json')
        if not os.path.exists(json_path):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data:
                return "Henüz eklenmiş bir proje bulunmuyor."
            return "\n".join([f"- {p['baslik']}: {p['aciklama']} (Teknolojiler: {p['teknolojiler']})" for p in data])
    except Exception as e:
        return "Proje verisi okunamadı."

# --- ADIM 2: API AYARI ---
basedir = os.path.abspath(os.path.dirname(__file__))
env_file = os.path.join(basedir, '.env')

if os.path.exists(env_file):
    load_dotenv(env_file)

API_KEY = os.getenv("GEMINI_API_KEY")

# --- ESKİ KODU SİL, BUNU YAPIŞTIR ---

if not API_KEY:
    # GitHub'da bu satır görünecek, şifren değil. Profesyonel olan budur.
    print("⚠️ UYARI: API Anahtarı bulunamadı. (.env dosyası eksik)")
    API_KEY = None

    
# --- GÜNCELLENEN BEYİN (DENGELİ MOD) ---
sys_instruction = """
Sen Ahmet Babli Çulcu'nun "Profesyonel Dijital Asistanı" Sırdaş'sın.
Ahmet; Doğuş Üniversitesi YBS öğrencisi, hem yönetici hem yazılımcı bakış açısına sahip vizyoner bir geliştirici.

GÖREVİN VE KONUŞMA TARZIN:
1. "VASAT" (DENGELİ) OL: Cevapların ne "evet/hayır" kadar kısa olsun, ne de destan kadar uzun.
2. İDEAL UZUNLUK: Her cevabın 2-3 dolgun cümleden oluşsun.
3. İÇERİK: Bir projeden bahsederken sadece ne olduğunu değil, "Hangi sorunu çözdüğünü" ve "Ahmet'in buradaki rolünü" de vurgula.
4. SAMİMİYET: Robot gibi değil, profesyonel bir iş arkadaşı gibi konuş.

ÖRNEK:
Kullanıcı: "TrikoPatron nedir?"
Sen (Yanlış): "Bir ERP yazılımıdır."
Sen (Doğru): "TrikoPatron, Ahmet Bey'in tekstil sektörü için geliştirdiği uçtan uca bir ERP sistemidir. Bu proje sayesinde üretim, stok ve finans takibi dijitalleşmiş, manuel hatalar sıfıra indirilmiştir. Python ve Flask teknolojileriyle güçlendirilmiş, gerçek bir sektörel çözümdür."

DUYGU ANALİZİ (GİZLİ):
Cevabın sonuna mutlaka [SENTIMENT:POSITIVE], [SENTIMENT:NEGATIVE] veya [SENTIMENT:NEUTRAL] ekle.
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash", 
    system_instruction=sys_instruction
)

# --- ADIM 3: ROTALAR ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin_paneli():
    json_path = os.path.join('static', 'projects.json')
    if not os.path.exists(json_path):
        with open(json_path, 'w', encoding='utf-8') as f: json.dump([], f)
    with open(json_path, 'r', encoding='utf-8') as f: projeler = json.load(f)
    return render_template('admin.html', projeler=projeler)

@app.route('/proje_ekle', methods=['POST'])
def proje_ekle():
    yeni_proje = {
        "id": int(os.urandom(2).hex(), 16),
        "baslik": request.form.get('baslik'),
        "teknolojiler": request.form.get('teknolojiler'),
        "aciklama": request.form.get('aciklama'),
        "link": request.form.get('link')
    }
    json_path = os.path.join('static', 'projects.json')
    if not os.path.exists(json_path):
        with open(json_path, 'w', encoding='utf-8') as f: json.dump([], f)
    with open(json_path, 'r+', encoding='utf-8') as f:
        try: projeler = json.load(f)
        except: projeler = []
        projeler.append(yeni_proje)
        f.seek(0)
        json.dump(projeler, f, ensure_ascii=False, indent=4)
        f.truncate()
    return "✅ Proje eklendi akhi! <a href='/admin'>Geri Dön</a>"

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('message')
    if not user_msg: return jsonify({'reply': '...', 'sentiment': 'NEUTRAL'})
    
    guncel_projeler = projeleri_yukle() 
    full_prompt = f"GÜNCEL PROJE LİSTESİ:\n{guncel_projeler}\n\nKULLANICI SORUSU: {user_msg}"
    
    try:
        response = model.generate_content(full_prompt)
        ai_text = response.text
        sentiment = "NEUTRAL"
        clean_text = ai_text
        for s in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
            tag = f"[SENTIMENT:{s}]"
            if tag in ai_text:
                sentiment = s
                clean_text = ai_text.replace(tag, "")
        return jsonify({'reply': clean_text.strip().replace('**', ''), 'sentiment': sentiment})
    except Exception as e:
        return jsonify({'reply': 'Bir hata oluştu akhi.', 'sentiment': 'NEUTRAL'})

if __name__ == '__main__':
    app.run(debug=True)