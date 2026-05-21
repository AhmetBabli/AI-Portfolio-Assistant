from app import create_app

# Sadece gerekeni import ettik
app = create_app()

with app.test_client() as client:
    response = client.post('/chat', json={"message": "Merhaba", "language": "tr"})
    
    print("Status:", response.status_code)
    
    # Gelen yanıtın JSON olduğundan emin oluyoruz
    if response.is_json:
        print("Response JSON:", response.get_json())
    else:
        print("Beklenmeyen Yanıt Formatı:", response.data.decode('utf-8'))