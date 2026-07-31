"""Geçici tanı script'i — /yonetici sayfasını test client ile tetikleyip
gerçek hatayı (varsa) ekrana basar. Konsol paste sorunu nedeniyle eklendi,
sorun çözülünce silinebilir."""
import traceback
from wsgi import app

app.config['TESTING'] = True
app.config['LOGIN_DISABLED'] = True

client = app.test_client()

try:
    response = client.get('/yonetici')
    print('STATUS:', response.status_code)
    print(response.get_data(as_text=True)[:3000])
except Exception:
    print('EXCEPTION RAISED:')
    traceback.print_exc()
