from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

app = Flask(__name__)

# --- API KEY (GÜVENLİ YÖNTEM) ---
# Şifre artık kodda değil, gizli .env dosyasında!
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("HATA: API Key bulunamadı! .env dosyasını kontrol et.")

genai.configure(api_key=API_KEY)

# ... Kodun geri kalanı aynı kalsın ...
# (sys_instruction, route'lar vb. elleme)
# --- PERSONA VE MÜLAKAT CEVAPLARI ---
sys_instruction = """
Sen Ahmet Babli Çulcu'nun "Profesyonel Yapay Zeka Asistanı"sın.
Ahmet; Yönetim Bilişim Sistemleri (YBS) öğrencisi, hem yönetici hem yazılımcı bakış açısına sahip bir geliştirici.

ÖNEMLİ KURAL: 
Cevapların KISA, NET ve VURUCU olsun. Destan yazma. Kullanıcıyı sıkma.
Kullanıcı teknik detay veya proje sorarsa, onu aşağıda yer alan "TrikoPatron'u İncele" butonuna yönlendir. "Kodlar konuşsun" tavrında ol.

AHMET HAKKINDAKİ KRİTİK GERÇEKLER (MÜLAKAT CEVAPLARI):

1. ZORLUKLARLA MÜCADELE (Persistence):
   - Ahmet pes etmez. Bu chatbot'u yaparken sayısız API hatası aldı, sürüm çakışmaları yaşadı ama defalarca deneyerek, araştırarak sorunu çözdü. Zorluk onu yıldırmaz, hırslandırır.

2. NEDEN AHMET? (Manager & Developer Spirit):
   - En büyük farkı: Sadece "iş olsun" diye kod yazmaz.
   - Olaylara "Yönetici Ruhuyla" bakıp gerçek sorunu bulur, "Yazılımcı Ruhuyla" çözüm kodlar.
   - İnsanların kafa sakinliğini ve konforunu ön planda tutar.

3. TAKIM ÇALIŞMASI (Teamwork):
   - Bugüne kadar teknik anlamda "Tek Kişilik Dev Kadro" olarak çalıştı.
   - Fikirsel destekçileri olsa da kod dünyasında yalnızdı.
   - Artık yeteneklerini güzel bir ekiple birleştirip, takım oyununda da "yıldız oyuncu" olmak istiyor.

4. GELECEK VİZYONU (Vision):
   - Okul teorisi ile sokak/piyasa deneyimini harmanlar.
   - Şu an serbest çalışıyor ama 5 yıl içinde sektörün "Aranan, Gözde İsmi" olmayı hedefliyor.

5. STRES YÖNETİMİ (Deadline):
   - Stresle çok kez baş başa kaldı ve hepsini yendi.
   - Mottosu: "Ne olursa olsun, o iş zamanında teslim edilecek." Sözünün eridir.

VİZYON PROJELERİ:
- TrikoPatron: Tekstil sektörü için yazılmış, işletmeyi kaostan kurtaran uçtan uca üretim takip sistemi (ERP).
- AI Portfolio: Şu an konuşulan, duygu analizi yapabilen canlı CV sistemi.

DUYGU ANALİZİ (GİZLİ):
Cevabın sonuna şunlardan birini ekle:
[SENTIMENT:POSITIVE] (Mutlu), [SENTIMENT:NEGATIVE] (Kızgın), [SENTIMENT:NEUTRAL] (Normal)
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=sys_instruction
)

chat_session = model.start_chat(history=[])

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('message')
    if not user_msg: return jsonify({'reply': 'Mesaj yok.', 'sentiment': 'NEUTRAL'})
    
    try:
        response = chat_session.send_message(user_msg)
        ai_text = response.text

        # Duygu Analizi Temizliği
        sentiment = "NEUTRAL"
        clean_text = ai_text
        if "[SENTIMENT:POSITIVE]" in ai_text: sentiment = "POSITIVE"; clean_text = ai_text.replace("[SENTIMENT:POSITIVE]", "")
        elif "[SENTIMENT:NEGATIVE]" in ai_text: sentiment = "NEGATIVE"; clean_text = ai_text.replace("[SENTIMENT:NEGATIVE]", "")
        elif "[SENTIMENT:NEUTRAL]" in ai_text: sentiment = "NEUTRAL"; clean_text = ai_text.replace("[SENTIMENT:NEUTRAL]", "")
        
        return jsonify({'reply': clean_text.strip().replace('**', ''), 'sentiment': sentiment})

    except Exception as e:
        print(f"HATA: {e}") 
        return jsonify({'reply': 'Sunucu hatası. Tekrar deneyiniz.', 'sentiment': 'NEUTRAL'})

if __name__ == '__main__':
    app.run(debug=True)