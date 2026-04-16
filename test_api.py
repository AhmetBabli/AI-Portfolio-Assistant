from flask import Flask
from config import Config
from models import Project, Setting
from extensions import db
from routes.chat import chat_bp
from app import create_app

app = create_app()

with app.app_context():
    print("API KEY in config:", app.config.get('GOOGLE_API_KEY'))
