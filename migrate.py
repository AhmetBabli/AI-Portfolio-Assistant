import os
import json
from extensions import db
from models import User, Project, Setting
from flask import Flask

def create_app():
    app = Flask(__name__)
    from config import Config
    app.config.from_object(Config)
    db.init_app(app)
    return app

def run_migration():
    app = create_app()
    with app.app_context():
        # Veritabanını oluştur
        db.create_all()
        
        # Admin kullanıcısını ekle
        admin_user = os.getenv("ADMIN_USER", "admin")
        admin_pass = os.getenv("ADMIN_PASS", "admin123")
        
        if not User.query.filter_by(username=admin_user).first():
            user = User(username=admin_user)
            user.set_password(admin_pass)
            db.session.add(user)
            print(f"Admin kullanıcısı '{admin_user}' veritabanına eklendi.")
            
        # JSON'dan projeleri taşı
        projects_file = os.path.join(app.config['STATIC_FOLDER'], 'projects.json')
        if os.path.exists(projects_file):
            try:
                with open(projects_file, 'r', encoding='utf-8') as f:
                    projeler = json.load(f)
                    added_projects = 0
                    for p in projeler:
                        if not Project.query.filter_by(baslik=p.get('baslik')).first():
                            project = Project(
                                baslik=p.get('baslik', ''),
                                teknolojiler=p.get('teknolojiler', ''),
                                aciklama=p.get('aciklama', ''),
                                link=p.get('link', ''),
                                gorsel=''
                            )
                            db.session.add(project)
                            added_projects += 1
                print(f"{added_projects} proje veritabanına aktarıldı.")
            except Exception as e:
                print(f"Projeler aktarılırken hata: {e}")
                
        # JSON'dan CV verisini taşı
        cv_file = os.path.join(app.config['STATIC_FOLDER'], 'cv_data.json')
        if os.path.exists(cv_file):
            defaults = {"hakkimda": "", "iletisim": "", "yetenekler": "", "sertifikalar": ""}
            try:
                with open(cv_file, 'r', encoding='utf-8') as f:
                    cv_data = json.load(f)
                    for k in defaults.keys():
                        v = cv_data.get(k, '')
                        setting = Setting.query.filter_by(key=k).first()
                        if not setting:
                            db.session.add(Setting(key=k, value=v))
                        else:
                            setting.value = v
                print("cv_data.json veritabanına aktarıldı.")
            except Exception as e:
                print(f"CV datası aktarılırken hata: {e}")
        else:
            # varsayılanları ekle
            defaults = {"hakkimda": "", "iletisim": "", "yetenekler": "", "sertifikalar": ""}
            for k, v in defaults.items():
                if not Setting.query.filter_by(key=k).first():
                  db.session.add(Setting(key=k, value=v))
                
        db.session.commit()
        print("Migrasyon başarıyla tamamlandı!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(BASE_DIR, '.env', '.env'))
    load_dotenv(os.path.join(BASE_DIR, '.env'))
    run_migration()
