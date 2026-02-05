import json
import os
import requests  # n8n ile iletişim için
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from functools import wraps

app = Flask(__name__)
app.secret_key = "AhmetBabli_Gizli_Anahtar"

# --- 🔗 SENİN VERDİĞİN GERÇEK n8n LİNKLERİ 🔗 ---

# 1. PDF İNDİREN (CV Oluşturucu) - O karmaşık kodlu olan bu:
N8N_PDF_MAKER_URL = "http://localhost:5678/webhook/e4555691-5339-4a83-80df-a645a111680e"

# 2. SİLME ve GÜNCELLEME YAPAN (Arka Plan) - webhook-sil olan bu:
N8N_UPDATER_URL = "http://localhost:5678/webhook/webhook-sil"


# --- KULLANICI BİLGİLERİ ---
ADMIN_USER = "ahmetbabli7"
ADMIN_PASS = "13868182894"

# --- DOSYA YOLLARI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
PROJECTS_FILE = os.path.join(STATIC_FOLDER, 'projects.json')
CV_DATA_FILE = os.path.join(STATIC_FOLDER, 'cv_data.json')

if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# 👇 API ANAHTARIN 👇
API_KEY = "" 

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        print(f"API Hatası: {e}")

# --- YARDIMCI FONKSİYONLAR ---
def veri_yukle(dosya_yolu):
    if not os.path.exists(dosya_yolu):
        if dosya_yolu == CV_DATA_FILE:
            return {"hakkimda": "", "iletisim": "", "yetenekler": "", "sertifikalar": ""}
        return []
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return [] if dosya_yolu == PROJECTS_FILE else {}

def veri_kaydet(dosya_yolu, veri):
    with open(dosya_yolu, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def n8n_veri_hazirla():
    """Tüm verileri n8n formatına hazırlar."""
    projeler = veri_yukle(PROJECTS_FILE)
    cv_data = veri_yukle(CV_DATA_FILE)
    if not cv_data: cv_data = {}

    projeler_text = ""
    for p in projeler:
        projeler_text += f"• {p['baslik']} ({p['teknolojiler']}): {p['aciklama']}\n"
    
    return {
        "hakkimda": cv_data.get('hakkimda', ''),
        "iletisim": cv_data.get('iletisim', ''), # JSON'da duruyor ama panelde gizli
        "yetenekler": cv_data.get('yetenekler', ''),
        "sertifikalar": cv_data.get('sertifikalar', ''),
        "projeler": projeler_text
    }

# --- GÜVENLİK ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- SAYFALAR ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_paneli'))
        else:
            return render_template('login.html', error="Hatalı giriş akhi!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/yonetici')
@login_required
def admin_paneli():
    projeler = veri_yukle(PROJECTS_FILE)
    cv_data = veri_yukle(CV_DATA_FILE)
    if not cv_data or not isinstance(cv_data, dict):
        cv_data = {"hakkimda": "", "iletisim": "", "yetenekler": "", "sertifikalar": ""}
    return render_template('admin.html', projeler=projeler, cv_data=cv_data)

# --- İŞLEMLER ---

@app.route('/proje_ekle', methods=['POST'])
@login_required
def proje_ekle():
    projeler = veri_yukle(PROJECTS_FILE)
    yeni_proje = {
        "id": int(os.urandom(4).hex(), 16),
        "baslik": request.form.get('baslik'),
        "teknolojiler": request.form.get('teknolojiler'),
        "aciklama": request.form.get('aciklama'),
        "link": request.form.get('link')
    }
    projeler.append(yeni_proje)
    veri_kaydet(PROJECTS_FILE, projeler)

    # Arka planda güncelleme yap (webhook-sil linkini kullanıyoruz çünkü güncelleme yapıyor)
    try:
        requests.post(N8N_UPDATER_URL, json=n8n_veri_hazirla(), timeout=1)
    except: pass

    return redirect(url_for('admin_paneli'))

@app.route('/proje_sil/<int:id>')
@login_required
def proje_sil(id):
    projeler = veri_yukle(PROJECTS_FILE)
    yeni_liste = [p for p in projeler if p.get('id') != id]
    veri_kaydet(PROJECTS_FILE, yeni_liste)
    
    # 🔴 BURASI 'webhook-sil' LINKINE GİDİYOR (Arka Plan Güncellemesi)
    try:
        requests.post(N8N_UPDATER_URL, json=n8n_veri_hazirla(), timeout=1)
        print("✅ n8n'e güncelleme haberi yollandı (webhook-sil)")
    except Exception as e:
        print(f"⚠️ n8n Hatası: {e}")

    return redirect(url_for('admin_paneli'))

@app.route('/cv_guncelle', methods=['POST'])
@login_required
def cv_guncelle():
    mevcut_veri = veri_yukle(CV_DATA_FILE)
    if not mevcut_veri: mevcut_veri = {}
    
    mevcut_veri["hakkimda"] = request.form.get('hakkimda')
    mevcut_veri["yetenekler"] = request.form.get('yetenekler')
    mevcut_veri["sertifikalar"] = request.form.get('sertifikalar')
    # iletisim'i ellemiyoruz, eskisi kalıyor.
    
    veri_kaydet(CV_DATA_FILE, mevcut_veri)
    return redirect(url_for('admin_paneli'))

# --- 🔥 KRİTİK BÖLÜM: CV İNDİRME 🔥 ---
@app.route('/cv_olustur')
@login_required
def cv_olustur_tetikle():
    payload = n8n_veri_hazirla()

    try:
        print("⏳ PDF İndiriliyor... (Ana Linke Gidiliyor)")
        # 🟢 BURASI SENİN KARMAŞIK KODLU OLAN LİNKE GİDİYOR (PDF Yapıcı)
        response = requests.post(N8N_PDF_MAKER_URL, json=payload, timeout=60)

        if response.status_code == 200:
            pdf_path = os.path.join(STATIC_FOLDER, 'Ahmet_Babli_CV.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            print("✅ PDF Geldi!")
            return send_file(pdf_path, as_attachment=True, download_name="Ahmet_Babli_CV.pdf")
        else:
            return f"n8n Hatası: {response.text}", 500
    except Exception as e:
        return f"Bağlantı hatası: {e}", 500

# --- CHATBOT ---
@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('message')
    if not user_msg: return jsonify({'response': '...', 'reply': '...'})
    
    cv_data = veri_yukle(CV_DATA_FILE)
    projeler = veri_yukle(PROJECTS_FILE)
    proje_metni = "\n".join([f"- {p['baslik']}: {p['aciklama']}" for p in projeler])
    
    full_prompt = (
        f"Sen Ahmet Babli Çulcu'nun asistanısın. Adın Sırdaş.\n"
        f"Ahmet: {cv_data.get('hakkimda')}\n"
        f"Projeler:\n{proje_metni}\n\n"
        f"Soru: {user_msg}"
    )
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(full_prompt)
        return jsonify({'response': response.text, 'reply': response.text})
    except:
        return jsonify({'response': "Bağlantı hatası.", 'reply': "Hata."})

if __name__ == '__main__':
    app.run(debug=True)