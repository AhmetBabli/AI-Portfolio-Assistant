from app import create_app

# Sadece ihtiyacımız olan create_app'i çağırdık
app = create_app()

with app.app_context():
    api_key = app.config.get('GOOGLE_API_KEY')
    
    if api_key:
        # Anahtarın sadece ilk 4 ve son 4 karakterini göster, ortasını yıldızla
        masked_key = f"{api_key[:4]}...{api_key[-4:]}"
        print(f"API KEY in config: Mevcut ({masked_key})")
    else:
        print("API KEY in config: BULUNAMADI (None)")