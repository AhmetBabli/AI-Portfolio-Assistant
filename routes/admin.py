import os
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import Project, Setting, ChatLog
from routes.auth import csrf_dogrula
from utils import get_settings, invalidate_cache

admin_bp = Blueprint('admin', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
CV_FILENAME = 'Ahmet_Babli_CV.pdf'


# ── Yardımcı fonksiyonlar ──────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    """Yalnızca izin verilen resim uzantılarına izin verir."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def _ensure_upload_dir(app):
    """Upload klasörünü gerekirse oluşturur."""
    ud = app.config['UPLOAD_FOLDER']
    if not os.path.exists(ud):
        os.makedirs(ud)
    return ud


def _unique_filename(original: str) -> str:
    """Dosya adına benzersiz prefix ekler (üzerine yazmayı önler)."""
    name, ext = os.path.splitext(secure_filename(original))
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"


# ── Admin ana sayfa ────────────────────────────────────────────────────────────

@admin_bp.route('/yonetici')
@login_required
def admin_paneli():
    projeler = Project.query.order_by(Project.id.desc()).all()
    cv_data = get_settings(use_cache=False)  # Admin her zaman taze veri görmeli

    # Sayaçlar için varsayılan
    for k in ("sayfa_goruntulenme", "toplam_mesaj"):
        cv_data.setdefault(k, "0")

    # Analitik
    yedi_gun_once = datetime.utcnow() - timedelta(days=7)
    haftalik_mesaj = ChatLog.query.filter(ChatLog.tarih >= yedi_gun_once).count()

    son_mesajlar = (
        ChatLog.query
        .order_by(ChatLog.tarih.desc())
        .limit(20)
        .all()
    )

    populer_gorsel = (
        db.session.query(
            ChatLog.gorsel_turu,
            db.func.count(ChatLog.gorsel_turu).label('sayi')
        )
        .group_by(ChatLog.gorsel_turu)
        .order_by(db.text('sayi DESC'))
        .limit(6)
        .all()
    )

    return render_template(
        'admin.html',
        projeler=[
            {
                "id": p.id, "baslik": p.baslik,
                "teknolojiler": p.teknolojiler,
                "aciklama": p.aciklama,
                "link": p.link, "gorsel": p.gorsel,
            }
            for p in projeler
        ],
        cv_data=cv_data,
        haftalik_mesaj=haftalik_mesaj,
        son_mesajlar=son_mesajlar,
        populer_gorsel=populer_gorsel,
    )


# ── Proje: Ekle ───────────────────────────────────────────────────────────────

@admin_bp.route('/proje_ekle', methods=['POST'])
@login_required
def proje_ekle():
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400

    baslik = (request.form.get('baslik') or '').strip()
    teknolojiler = (request.form.get('teknolojiler') or '').strip()
    aciklama = (request.form.get('aciklama') or '').strip()
    link = (request.form.get('link') or '').strip()

    gorsel_path = ''
    if 'foto' in request.files:
        foto = request.files['foto']
        if foto.filename and allowed_file(foto.filename):
            filename = _unique_filename(foto.filename)
            ud = _ensure_upload_dir(current_app)
            foto.save(os.path.join(ud, filename))
            gorsel_path = f"uploads/{filename}"

    db.session.add(Project(
        baslik=baslik, teknolojiler=teknolojiler,
        aciklama=aciklama, link=link, gorsel=gorsel_path
    ))
    db.session.commit()
    invalidate_cache('projects_text')
    return redirect(url_for('admin.admin_paneli'))


# ── Proje: Güncelle ───────────────────────────────────────────────────────────

@admin_bp.route('/proje_guncelle/<int:id>', methods=['POST'])
@login_required
def proje_guncelle(id):
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400

    proje = Project.query.get_or_404(id)
    proje.baslik = (request.form.get('baslik') or proje.baslik).strip()
    proje.teknolojiler = (request.form.get('teknolojiler') or proje.teknolojiler).strip()
    proje.aciklama = (request.form.get('aciklama') or proje.aciklama).strip()
    proje.link = (request.form.get('link') or proje.link or '').strip()

    if 'foto' in request.files:
        foto = request.files['foto']
        if foto.filename and allowed_file(foto.filename):
            filename = _unique_filename(foto.filename)
            ud = _ensure_upload_dir(current_app)
            foto.save(os.path.join(ud, filename))
            proje.gorsel = f"uploads/{filename}"

    db.session.commit()
    invalidate_cache('projects_text')
    return redirect(url_for('admin.admin_paneli'))


# ── Proje: Sil ────────────────────────────────────────────────────────────────

@admin_bp.route('/proje_sil/<int:id>', methods=['POST'])
@login_required
def proje_sil(id):
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400

    proje = Project.query.get_or_404(id)
    
    # Dosya silme işlemini güvenli ve robust yap
    if proje.gorsel:
        full_path = os.path.join(current_app.config['STATIC_FOLDER'], proje.gorsel)
        try:
            if os.path.exists(full_path) and os.path.isfile(full_path):
                # Path traversal kontrolü
                if not os.path.abspath(full_path).startswith(
                    os.path.abspath(current_app.config['STATIC_FOLDER'])
                ):
                    current_app.logger.error(f"Path traversal attempt detected: {full_path}")
                    return "Dosya silme başarısız.", 400
                
                os.remove(full_path)
                current_app.logger.info(f"Deleted file: {full_path}")
        except OSError as e:
            current_app.logger.error(f"File deletion error: {e}")
            # Dosya silme başarısız olsa da DB'den sil
    
    # Database'den sil
    try:
        db.session.delete(proje)
        db.session.commit()
        invalidate_cache('projects_text')
        return redirect(url_for('admin.admin_paneli'))
    except Exception as e:
        current_app.logger.error(f"Project deletion error: {e}")
        db.session.rollback()
        return "Proje silme işlemi başarısız.", 500


# ── Ayarlar: Güncelle ─────────────────────────────────────────────────────────

@admin_bp.route('/ayar_guncelle', methods=['POST'])
@login_required
def ayar_guncelle():
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400

    alanlar = ['hakkimda', 'iletisim', 'yetenekler', 'sertifikalar', 'prompt_ek_bilgi']
    for key in alanlar:
        val = (request.form.get(key) or '').strip()
        s = Setting.query.filter_by(key=key).first()
        if s:
            s.value = val
        else:
            db.session.add(Setting(key=key, value=val))
    db.session.commit()
    invalidate_cache('settings')
    return redirect(url_for('admin.admin_paneli') + '?tab=icerik')


# ── CV PDF: Yükle ─────────────────────────────────────────────────────────────

def _validate_pdf(file_obj, max_size_mb=5):
    """PDF dosya validasyonu - magic bytes ve size kontrolü."""
    # 1. Magic bytes kontrolü (PDF header)
    file_obj.seek(0)
    header = file_obj.read(4)
    if header != b'%PDF':
        return False, "Geçersiz PDF dosyası"
    
    # 2. Size kontrolü
    file_obj.seek(0, 2)  # End'e git
    size = file_obj.tell()
    if size > max_size_mb * 1024 * 1024:
        return False, f"Dosya çok büyük (maximum {max_size_mb}MB)"
    
    return True, "OK"

@admin_bp.route('/cv_pdf_yukle', methods=['POST'])
@login_required
def cv_pdf_yukle():
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400
    
    if 'cv_pdf' not in request.files:
        return redirect(url_for('admin.admin_paneli') + '?tab=icerik')
    
    pdf = request.files['cv_pdf']
    if not pdf.filename:
        return redirect(url_for('admin.admin_paneli') + '?tab=icerik')
    
    # Filename validasyonu
    if not pdf.filename.lower().endswith('.pdf'):
        current_app.logger.warning(f"Invalid file type attempted: {pdf.filename}")
        return render_template('admin.html', error="Sadece PDF dosyaları yüklenebilit.")
    
    # PDF validasyonu
    is_valid, msg = _validate_pdf(pdf)
    if not is_valid:
        current_app.logger.warning(f"PDF validation failed: {msg}")
        return render_template('admin.html', error=msg)
    
    save_path = os.path.join(current_app.config['STATIC_FOLDER'], CV_FILENAME)
    
    # Backup eski dosya
    backup_path = save_path + ".backup"
    if os.path.exists(save_path):
        try:
            os.rename(save_path, backup_path)
        except OSError as e:
            current_app.logger.error(f"Backup error: {e}")
    
    try:
        pdf.seek(0)  # Reset file pointer
        pdf.save(save_path)
        current_app.logger.info(f"PDF uploaded successfully: {save_path}")
        return redirect(url_for('admin.admin_paneli') + '?tab=icerik')
    except Exception as e:
        current_app.logger.error(f"PDF save error: {e}")
        # Backup'dan geri yükle
        if os.path.exists(backup_path):
            try:
                os.rename(backup_path, save_path)
            except OSError:
                pass
        return render_template('admin.html', error="PDF yükleme hatası")
