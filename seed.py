"""
Uygulama her başladığında çağrılır (create_app içinden).
Ephemeral dosya sistemi nedeniyle her deploy'da veritabanı sıfırlanabildiği
için, admin kullanıcısını ve static/projects.json'daki projeleri
idempotent şekilde (var olanı atlayarak) yeniden oluşturur.
Manuel migrate.py'nin aksine env değişkenleri eksikse patlamaz — sadece
uyarı loglayıp devam eder, çünkü bu boot-time bir güvenlik ağı.
"""

import json
import os

from models import Project, Setting, User

_DEFAULT_SETTINGS = {
    "hakkimda": "",
    "iletisim": "",
    "yetenekler": "",
    "sertifikalar": "",
    "prompt_ek_bilgi": "",
}


def seed_database(app, db):
    with app.app_context():
        try:
            admin_user = os.getenv("ADMIN_USER")
            admin_pass = os.getenv("ADMIN_PASS")

            if not admin_user or not admin_pass:
                app.logger.warning("Seed: ADMIN_USER/ADMIN_PASS tanımlı değil, admin kullanıcısı atlandı.")
            elif not User.query.filter_by(username=admin_user).first():
                user = User(username=admin_user)
                user.set_password(admin_pass)
                db.session.add(user)
                app.logger.info("Seed: admin kullanıcısı '%s' oluşturuldu.", admin_user)

            projects_file = os.path.join(app.config.get('STATIC_FOLDER', 'static'), 'projects.json')
            if os.path.exists(projects_file):
                with open(projects_file, 'r', encoding='utf-8') as f:
                    for p in json.load(f):
                        if not Project.query.filter_by(baslik=p.get('baslik')).first():
                            db.session.add(Project(
                                baslik=p.get('baslik', ''),
                                teknolojiler=p.get('teknolojiler', ''),
                                aciklama=p.get('aciklama', ''),
                                link=p.get('link', ''),
                                gorsel=p.get('gorsel', ''),
                            ))

            for key, val in _DEFAULT_SETTINGS.items():
                if not Setting.query.filter_by(key=key).first():
                    db.session.add(Setting(key=key, value=val))

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.warning("Seed sırasında hata: %s", e)
