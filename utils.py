"""
Sırdaş AI — Ortak yardımcı fonksiyonlar.
Mükerrer kodları merkezileştirerek DRY prensibini sağlar.
"""

import hashlib
import time
import threading
import re

from flask import current_app
from extensions import db
from models import Setting, Project


# ── Advanced TTL Cache Manager ────────────────────────────────────────────────
class CacheManager:
    """Thread-safe cache manager with configurable TTL per key."""
    
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
    
    def get(self, key: str):
        """Cache'ten veri döner, TTL geçmişse None döner."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if (time.time() - entry['ts']) < entry['ttl']:
                    return entry['data']
                else:
                    # Süresi dolmuş veriyi bellekte tutma, temizle
                    del self._cache[key]
        return None
    
    def set(self, key: str, data, ttl: int = 60):
        """Cache'e veri yazar. TTL (saniye) dışarıdan parametre olarak alınır."""
        with self._lock:
            self._cache[key] = {'data': data, 'ts': time.time(), 'ttl': ttl}
    
    def invalidate(self, key: str = None):
        """Cache'i temizler. key verilmezse tamamını siler."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif key is None:
                self._cache.clear()


# Global cache manager instance
_cache_manager = CacheManager()


def get_settings(use_cache: bool = True) -> dict:
    """Setting tablosunun tamamını sözlük olarak döner. TTL cache destekli."""
    if use_cache:
        cached = _cache_manager.get('settings')
        if cached is not None:
            return cached

    result = {s.key: s.value for s in Setting.query.all()}

    if use_cache:
        # Settings için 5 dakika (300 saniye) TTL
        _cache_manager.set('settings', result, ttl=300)

    return result


def get_projects(use_cache: bool = True) -> list:
    """Projeleri veritabanından çeker. Sadece veri döner (Separation of Concerns)."""
    if use_cache:
        cached = _cache_manager.get('projects')
        if cached is not None:
            return cached

    projeler = Project.query.all()
    
    if use_cache:
        # Projeler için 10 dakika (600 saniye) TTL
        _cache_manager.set('projects', projeler, ttl=600)
        
    return projeler


def format_projects_for_prompt(projeler: list) -> str:
    """Çekilen proje nesnelerini LLM promptuna uygun metne çevirir."""
    return "\n".join([
        f"- {p.baslik} ({p.teknolojiler}): {p.aciklama}"
        for p in projeler
    ])


def get_projects_text() -> str:
    """Geriye dönük uyumluluk (Backward Compatibility) için eski fonksiyon."""
    projeler = get_projects()
    return format_projects_for_prompt(projeler)


def invalidate_cache(key: str = None):
    """Cache'i temizler. key verilmezse tamamını siler."""
    _cache_manager.invalidate(key)


# ── Advanced Güvenlik Yardımcıları ────────────────────────────────────────────

def sanitize_input(msg: str, max_length: int = 2000) -> str:
    """Advanced prompt injection prevention."""
    if not msg:
        return ""
    
    # 1. Uzunluk kontrolünü en başta yap (Performans için)
    if len(msg) > max_length:
        msg = msg[:max_length]
    
    # 2. Tehlikeli pattern'leri regex ile sil
    dangerous_patterns = [
        r'(?i)<\s*script[^>]*>.*?<\s*/\s*script\s*>',  # HTML script tags
        r'(?i)javascript\s*:',                          # JS protocol
        r'\[\[.*?\]\]',                                  # Bracket notation
        r'{{.*?}}',                                      # Template injection
        r'{%.*?%}',                                      # Jinja injection
        r'<<SYS>>|<\|im_start\|>|<<\/SYS>>',           # LLM control sequences
        r'\[INST\]|\[/INST\]',                          # LLaMA format
    ]
    
    for pattern in dangerous_patterns:
        msg = re.sub(pattern, '', msg, flags=re.IGNORECASE)
    
    # NOT: Kullanıcının geçerli kod veya JSON atabilmesi için
    # %30 özel karakter kısıtlaması kaldırıldı.
    
    return msg.strip()


def ip_hash(ip: str) -> str:
    """IP adresini anonim hash'e çevirir (KVKK uyumlu, Salted Hash ile güvenli)."""
    ip_str = ip or '0.0.0.0'
    
    # Flask app context içinden SECRET_KEY'i tuz (salt) olarak alıyoruz.
    # Eğer app context dışında (örn. background task) çağrılırsa hata almamak için try/except kullanıyoruz.
    try:
        salt = current_app.config.get('SECRET_KEY', 'default-dev-salt')
    except RuntimeError:
        salt = 'default-dev-salt'
        
    salted_ip = f"{ip_str}:{salt}"
    
    return hashlib.sha256(salted_ip.encode()).hexdigest()[:32]