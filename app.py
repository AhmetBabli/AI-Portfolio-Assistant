import json
import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = "AhmetBabli_Gizli_Anahtar"

# --- KULLANICI ADI VE ŞİFRE ---
ADMIN_USER = "ahmetbabli7"
ADMIN_PASS = "13868182894"

# --- DOSYA YOLLARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
PROJECTS_FILE = os.path.join(STATIC_FOLDER, 'projects.json')

if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# 👇 API ANAHTARIN (Senin istediğin gibi açıkta bıraktım) 👇
API_KEY = "AIzaSyB6tdcFxNirbvU441ROK5rtM5tQ5p6iNwo"

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        print(f"API Hatası: {e}")

# --- SIRDAŞ ---
sys_instruction = """
Sen Ahmet Babli Çulcu'nun asistanı Sırdaş'sın.
Ahmet YBS öğrencisidir. Projeleri ve yetenekleri hakkında kısa, net ve profesyonel bilgi ver.
Duygu analizi yapma.
"""

# --- GÜVENLİK KİLİDİ ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# --- YARDIMCI FONKSİYONLAR (DÜZELTİLMİŞ HALİ) ---
def projeleri_yukle():
    try:
        if not os.path.exists(PROJECTS_FILE): return "Henüz proje girilmemiş."
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # AI'a gidecek metni hazırlıyoruz (Artık Teknolojileri de içeriyor!)
            metin = ""
            for p in data:
                teknoloji = p.get('teknolojiler', 'Belirtilmedi')
                metin += f"- PROJE ADI: {p['baslik']}\n"
                metin += f"  KULLANILAN TEKNOLOJİLER: {teknoloji}\n"
                metin += f"  AÇIKLAMA: {p['aciklama']}\n"
                metin += f"  LİNK: {p.get('link', 'Yok')}\n\n"

            return metin
    except Exception as e:
        return f"Veri okunurken hata oluştu: {e}"

# --- SAYFALAR ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kadi = request.form.get('username')
        sifre = request.form.get('password')

        if kadi == ADMIN_USER and sifre == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_paneli'))
        else:
            return render_template('login.html', error="Hatalı kullanıcı adı veya şifre!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/yonetici')
@login_required
def admin_paneli():
    if not os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
    with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
        projeler = json.load(f)
    return render_template('admin.html', projeler=projeler)

@app.route('/proje_ekle', methods=['POST'])
@login_required
def proje_ekle():
    try:
        # YENİ EKLENEN KISIM: Her projeye rastgele bir sayı (ID) veriyoruz ki silebilelim
        yeni_proje = {
            "id": int(os.urandom(4).hex(), 16),
            "baslik": request.form.get('baslik'),
            "teknolojiler": request.form.get('teknolojiler'),
            "aciklama": request.form.get('aciklama'),
            "link": request.form.get('link')
        }
        if not os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
        with open(PROJECTS_FILE, 'r+', encoding='utf-8') as f:
            try: projeler = json.load(f)
            except: projeler = []
            projeler.append(yeni_proje)
            f.seek(0)
            json.dump(projeler, f, ensure_ascii=False, indent=4)
            f.truncate()
        return "✅ Proje eklendi akhi! <a href='/yonetici'>Geri Dön</a>"
    except Exception as e:
        return f"Hata: {e}"

# --- YENİ EKLENEN SİLME FONKSİYONU ---
@app.route('/proje_sil/<int:id>')
@login_required
def proje_sil(id):
    if not os.path.exists(PROJECTS_FILE):
        return redirect(url_for('admin_paneli'))

    with open(PROJECTS_FILE, 'r+', encoding='utf-8') as f:
        try:
            projeler = json.load(f)
            # ID'si eşleşmeyenleri yeni listeye al (yani eşleşeni at)
            yeni_liste = [p for p in projeler if p.get('id') != id]

            f.seek(0)
            json.dump(yeni_liste, f, ensure_ascii=False, indent=4)
            f.truncate()
        except: pass

    return redirect(url_for('admin_paneli'))

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('message')
    if not user_msg: return jsonify({'response': '...', 'reply': '...'})

    full_prompt = f"PROJELER:\n{projeleri_yukle()}\n\nSORU: {user_msg}"

    try:
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=sys_instruction)
        response = model.generate_content(full_prompt)
        return jsonify({'response': response.text, 'reply': response.text, 'sentiment': 'NEUTRAL'})
    except:
        return jsonify({'response': "Hata oluştu.", 'reply': "Hata oluştu.", 'sentiment': 'NEUTRAL'})

if __name__ == '__main__':
    app.run(debug=True)