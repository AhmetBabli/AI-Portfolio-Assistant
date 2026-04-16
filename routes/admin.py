import os
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
from models import Project, Setting
from extensions import db
from routes.auth import csrf_dogrula

admin_bp = Blueprint('admin', __name__)

def get_settings():
    settings_obj = Setting.query.all()
    cv_data = {}
    for s in settings_obj:
        cv_data[s.key] = s.value
    return cv_data

@admin_bp.route('/yonetici')
@login_required
def admin_paneli():
    projeler = Project.query.all()
    cv_data = get_settings()
    for k in ["sayfa_goruntulenme", "toplam_mesaj"]:
        if k not in cv_data:
            cv_data[k] = ""
    return render_template('admin.html', projeler=[{
        "id": p.id,
        "baslik": p.baslik,
        "teknolojiler": p.teknolojiler,
        "aciklama": p.aciklama,
        "link": p.link,
        "gorsel": p.gorsel
    } for p in projeler], cv_data=cv_data)

@admin_bp.route('/proje_ekle', methods=['POST'])
@login_required
def proje_ekle():
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400
        
    baslik = request.form.get('baslik')
    teknolojiler = request.form.get('teknolojiler')
    aciklama = request.form.get('aciklama')
    link = request.form.get('link')
    
    gorsel_path = ""
    if 'foto' in request.files:
        foto = request.files['foto']
        if foto.filename != '':
            filename = secure_filename(foto.filename)
            upload_dir = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            foto_path = os.path.join(upload_dir, filename)
            foto.save(foto_path)
            gorsel_path = f"uploads/{filename}"

    yeni_proje = Project(
        baslik=baslik,
        teknolojiler=teknolojiler,
        aciklama=aciklama,
        link=link,
        gorsel=gorsel_path
    )
    db.session.add(yeni_proje)
    db.session.commit()
    return redirect(url_for('admin.admin_paneli'))

@admin_bp.route('/proje_sil/<int:id>', methods=['POST'])
@login_required
def proje_sil(id):
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400
        
    proje = Project.query.get_or_404(id)
    if proje.gorsel:
        full_path = os.path.join(current_app.config['STATIC_FOLDER'], proje.gorsel)
        if os.path.exists(full_path):
            os.remove(full_path)
            
    db.session.delete(proje)
    db.session.commit()
    return redirect(url_for('admin.admin_paneli'))

    
    
@admin_bp.route('/cv_pdf_yukle', methods=['POST'])
@login_required
def cv_pdf_yukle():
    if not csrf_dogrula():
        return "Geçersiz CSRF token.", 400
        
    if 'cv_pdf' in request.files:
        pdf_file = request.files['cv_pdf']
        if pdf_file.filename != '' and pdf_file.filename.endswith('.pdf'):
            save_path = os.path.join(current_app.config['STATIC_FOLDER'], 'Ahmet_Babli_CV.pdf')
            pdf_file.save(save_path)
            
    return redirect(url_for('admin.admin_paneli'))
