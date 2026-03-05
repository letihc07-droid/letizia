# security.py — Sanitización, validación y helpers de tokens
import re
import hashlib
import secrets
import uuid
import bleach
from datetime import datetime, timezone


# ── Sanitización ──────────────────────────────────────────────

def sanitize_text(value: str, max_len: int = 500) -> str:
    """Elimina HTML/JS malicioso y limita longitud."""
    if not isinstance(value, str):
        return ''
    clean = bleach.clean(value, tags=[], strip=True)
    clean = clean.replace('\x00', '')
    return clean.strip()[:max_len]


# ── Validaciones ──────────────────────────────────────────────

def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$', email)) and len(email) <= 254

def is_valid_username(username: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_]{3,30}$', username))

def is_valid_password(password: str) -> bool:
    """Mínimo 8 chars, al menos una mayúscula y un número."""
    if not isinstance(password, str):
        return False
    if len(password) < 8 or len(password) > 128:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value), version=4)
        return True
    except (ValueError, AttributeError):
        return False

def is_valid_zip(zip_code: str) -> bool:
    return bool(re.match(r'^\d{5}$', str(zip_code)))


# ── Tokens ────────────────────────────────────────────────────

def generate_refresh_token() -> tuple[str, str]:
    """Devuelve (token_raw, token_hash_sha256)."""
    raw    = secrets.token_hex(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed

def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def new_uuid() -> str:
    return str(uuid.uuid4())

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


# ── Respuestas de error seguras ───────────────────────────────

def safe_error(message: str, status: int):
    """Error sin stack traces ni info interna."""
    from flask import jsonify
    return jsonify({'error': message}), status
