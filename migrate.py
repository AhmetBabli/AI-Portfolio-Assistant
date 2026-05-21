import os
import json
from dotenv import load_dotenv

# 1. Ortam değişkenlerini her şeyden ÖNCE yükle!
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

from extensions import db
from models import User, Project, Setting
from app import create_app

_DEFAULT_SETTINGS = {
    "hakkimda": "",
    "iletisim": "",
    "yetenekler": "",
    "sertifikalar": "",
    "prompt_ek_bilgi": "",
}

def run_migration():
    app = create_app()
    with app.app_context():
        # Veritabanı tablolarını oluştur
        db.create_all()

        try:
            # --- ADMİN KULLANICI İŞLEMİ ---
            admin_user = os.getenv("ADMIN_USER")
            admin_pass = os.getenv("ADMIN_PASS")

            # Güvenlik (Fail-Fast): Şifre yoksa işlemi reddet
            if not admin_user or not admin_pass:
                raise ValueError("Kritik Hata: .env dosyasında ADMIN_USER veya ADMIN_PASS bulunamadı! Güvenlik için varsayılan şifre kullanılmıyor.")

            if not User.query.filter_by(username=admin_user).first():
                user = User(username=admin_user)
                user.set_password(admin_pass)
                db.session.add(user)
                print(f"[+] Admin kullanıcısı '{admin_user}' hazır.")

            # --- PROJELERİ AKTARMA ---
            projects_file = os.path.join(app.config.get('STATIC_FOLDER', 'static'), 'projects.json')
            if os.path.exists(projects_file):
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
                print(f"[+] {added_projects} yeni proje eklendi.")

            # --- CV VERİSİNİ AKTARMA ---
            cv_file = os.path.join(app.config.get('STATIC_FOLDER', 'static'), 'cv_data.json')
            if os.path.exists(cv_file):
                with open(cv_file, 'r', encoding='utf-8') as f:
                    cv_data = json.load(f)
                    for k in _DEFAULT_SETTINGS:
                        # Eğer değer string değilse string'e çevirerek patlamayı önle
                        v = str(cv_data.get(k, '')) 
                        setting = Setting.query.filter_by(key=k).first()
                        if not setting:
                            db.session.add(Setting(key=k, value=v))
                        else:
                            setting.value = v
                print("[+] cv_data.json ayarlara başarıyla aktarıldı.")
            else:
                # Varsayılanları ekle
                for k, v in _DEFAULT_SETTINGS.items():
                    if not Setting.query.filter_by(key=k).first():
                        db.session.add(Setting(key=k, value=v))
                print("[+] Varsayılan ayarlar eklendi.")

            # Her şey yolundaysa kaydet!
            db.session.commit()
            print("\n🚀 Migrasyon başarıyla ve güvenle tamamlandı!")

        except Exception as e:
            # Hata durumunda yapılan tüm eklemeleri geri al (Rollback)
            db.session.rollback()
            print(f"\n❌ KRİTİK HATA! İşlemler iptal edildi (Rollback yapıldı).\nHata detayı: {e}")


if __name__ == "__main__":
    run_migration()