from flask import Flask
from config import Config
from models import Project, Setting
from extensions import db
from routes.chat import chat_bp
from app import create_app

app = create_app()

with app.test_client() as client:
    response = client.post('/chat', json={"message": "Merhaba", "language": "tr"})
    print("Status:", response.status_code)
    print("Response JSON:", response.get_json())
