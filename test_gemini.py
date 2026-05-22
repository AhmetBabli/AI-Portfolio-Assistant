#!/usr/bin/env python
"""Gemini API bağlantı testi"""

import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

API_KEY = os.getenv("GOOGLE_API_KEY")

print(f"API Key yüklendi: {'✓' if API_KEY else '✗'}")
if API_KEY:
    print(f"API Key uzunluğu: {len(API_KEY)} karakter")
    print(f"API Key başı: {API_KEY[:10]}...")

try:
    import google.generativeai as genai
    print("✓ google.generativeai modülü yüklendi")
    
    genai.configure(api_key=API_KEY)
    print("✓ Gemini API yapılandırıldı")
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    print("✓ Model oluşturuldu")
    
    response = model.generate_content("Merhaba! Çalışıyor musun?")
    print("✓ API çağrısı başarılı!")
    print(f"Cevap: {response.text[:100]}")
    
except Exception as e:
    print(f"✗ HATA: {type(e).__name__}: {str(e)}")
