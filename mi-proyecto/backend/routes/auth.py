# routes/auth.py — Autenticación: registro, login, refresh, logout
import os
import bcrypt
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from database import get_connection
from security import (
    sanitize_text, is_valid_email, is_valid_username, is_valid_password,
    generate_refresh_token, hash_refresh_token, new_uuid, safe_error,
)

auth_bp = Blueprint('auth', __name__)

BCRYPT_ROUNDS = 12   # ~250 ms por hash


# ════════════════════════════════════════════
# POST /api/auth/register
# ════════════════════════════════════════════
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not data:
        return safe_error('Body JSON requerido.', 400)

    username = sanitize_text(data.get('username', ''), 30)
    email    = sanitize_text(data.get('email', ''), 254).lower().strip()
    password = data.get('password', '')
    confirm  = data.get('confirmPassword', '')

    # Validaciones
    errors = {}
    if not is_valid_username(username):
        errors['username'] = 'Username: 3–30 caracteres, solo letras, números y _'
    if not is_valid_email(email):
        errors['email'] = 'Email no válido.'
    if not is_valid_password(password):
        errors['password'] = 'Contraseña: mínimo 8 caracteres, una mayúscula y un número.'
    if password != confirm:
        errors['confirmPassword'] = 'Las contraseñas no coinciden.'
    if errors:
        return jsonify({'error': 'Datos inválidos.', 'fields': errors}), 422

    conn = get_connection()
    try:
        # Comprobar duplicados
        if conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            bcrypt.hashpw(b'timing_prevention', bcrypt.gensalt(BCRYPT_ROUNDS))
            return safe_error('Ese email ya está registrado.', 409)
        if conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            return safe_error('Ese nombre de usuario ya está en uso.', 409)

        # Hash de contraseña
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(BCRYPT_ROUNDS)).decode('utf-8')
        user_id = new_uuid()

        conn.execute(
            'INSERT INTO users (id, username, email, password) VALUES (?, ?, ?, ?)',
            (user_id, username, email, pw_hash)
        )
        conn.commit()

        access_token     = create_access_token(identity=user_id)
        raw_rt, hash_rt  = generate_refresh_token()
        _store_refresh(conn, user_id, hash_rt)
        conn.commit()

        resp = make_response(jsonify({
            'message':     'Cuenta creada.',
            'accessToken': access_token,
            'user': {'id': user_id, 'username': username, 'email': email, 'role': 'user'},
        }), 201)
        _set_rt_cookie(resp, raw_rt)
        return resp

    except Exception as e:
        conn.rollback()
        print(f'[register ERROR] {e}')
        return safe_error('Error interno del servidor.', 500)
    finally:
        conn.close()


# ════════════════════════════════════════════
# POST /api/auth/login
# ════════════════════════════════════════════
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not data:
        return safe_error('Body JSON requerido.', 400)

    email    = sanitize_text(data.get('email', ''), 254).lower().strip()
    password = data.get('password', '')

    if not is_valid_email(email) or not password:
        return safe_error('Credenciales incorrectas.', 401)

    conn = get_connection()
    try:
        # Bloqueo por fuerza bruta: 5 fallos en 15 min
        fails = conn.execute("""
            SELECT COUNT(*) as n FROM login_attempts
            WHERE identifier = ? AND success = 0
            AND created_at > strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')
        """, (email,)).fetchone()['n']

        if fails >= 5:
            return safe_error('Cuenta bloqueada temporalmente. Espera 15 minutos.', 429)

        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        # Siempre ejecutar bcrypt (evita timing attacks)
        dummy = b'$2b$12$invalidhashXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
        stored_hash = user['password'].encode() if user else dummy
        match = bcrypt.checkpw(password.encode('utf-8'), stored_hash)

        if not user or not match:
            _log_attempt(conn, email, request.remote_addr, success=False)
            conn.commit()
            return safe_error('Credenciales incorrectas.', 401)

        if not user['is_active']:
            return safe_error('Cuenta desactivada. Contacta con soporte.', 403)

        access_token    = create_access_token(identity=user['id'])
        raw_rt, hash_rt = generate_refresh_token()
        _store_refresh(conn, user['id'], hash_rt)
        _log_attempt(conn, email, request.remote_addr, success=True)
        conn.commit()

        resp = make_response(jsonify({
            'message':     'Sesión iniciada.',
            'accessToken': access_token,
            'user': {
                'id':       user['id'],
                'username': user['username'],
                'email':    user['email'],
                'role':     user['role'],
            },
        }))
        _set_rt_cookie(resp, raw_rt)
        return resp

    except Exception as e:
        conn.rollback()
        print(f'[login ERROR] {e}')
        return safe_error('Error interno del servidor.', 500)
    finally:
        conn.close()


# ════════════════════════════════════════════
# POST /api/auth/refresh — Rota el refresh token
# ════════════════════════════════════════════
@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    raw_token = request.cookies.get('refreshToken')
    if not raw_token:
        return safe_error('Refresh token no encontrado.', 401)

    token_hash = hash_refresh_token(raw_token)
    conn = get_connection()
    try:
        stored = conn.execute("""
            SELECT rt.*, u.id as uid, u.username, u.role, u.is_active
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.token_hash = ?
        """, (token_hash,)).fetchone()

        if not stored:
            return safe_error('Token inválido.', 401)

        if stored['revoked']:
            # Token reutilizado → posible robo → revocar todos
            conn.execute('UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?', (stored['user_id'],))
            conn.commit()
            resp = make_response(jsonify({'error': 'Sesión revocada por seguridad.'}), 401)
            _clear_rt_cookie(resp)
            return resp

        expires = datetime.fromisoformat(stored['expires_at'].replace('Z', '+00:00'))
        if expires < datetime.now(timezone.utc):
            return safe_error('Sesión expirada. Inicia sesión de nuevo.', 401)

        if not stored['is_active']:
            return safe_error('Cuenta inactiva.', 403)

        # Rotar token
        conn.execute('UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?', (token_hash,))
        new_raw, new_hash = generate_refresh_token()
        _store_refresh(conn, stored['uid'], new_hash)
        conn.commit()

        new_access = create_access_token(identity=stored['uid'])
        resp = make_response(jsonify({'accessToken': new_access}))
        _set_rt_cookie(resp, new_raw)
        return resp

    except Exception as e:
        print(f'[refresh ERROR] {e}')
        return safe_error('Error interno.', 500)
    finally:
        conn.close()


# ════════════════════════════════════════════
# POST /api/auth/logout
# ════════════════════════════════════════════
@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    # Funciona aunque el token ya haya expirado
    raw_token = request.cookies.get('refreshToken')
    if raw_token:
        token_hash = hash_refresh_token(raw_token)
        conn = get_connection()
        try:
            conn.execute('UPDATE refresh_tokens SET revoked = 1 WHERE token_hash = ?', (token_hash,))
            conn.commit()
        finally:
            conn.close()
    resp = make_response(jsonify({'message': 'Sesión cerrada.'}))
    _clear_rt_cookie(resp)
    return resp


# ════════════════════════════════════════════
# GET /api/auth/me
# ════════════════════════════════════════════
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    conn = get_connection()
    try:
        user = conn.execute(
            'SELECT id, username, email, role, created_at FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        if not user:
            return safe_error('Usuario no encontrado.', 404)
        return jsonify({'user': dict(user)})
    finally:
        conn.close()


# ── Helpers privados ──────────────────────────────────────────

def _store_refresh(conn, user_id: str, token_hash: str):
    expires = (datetime.now(timezone.utc) + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    conn.execute(
        'INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)',
        (new_uuid(), user_id, token_hash, expires)
    )

def _log_attempt(conn, identifier: str, ip: str, success: bool):
    try:
        conn.execute(
            'INSERT INTO login_attempts (identifier, ip, success) VALUES (?, ?, ?)',
            (identifier, ip or 'unknown', 1 if success else 0)
        )
    except Exception:
        pass

def _cookie_kwargs() -> dict:
    is_prod = os.getenv('FLASK_ENV', 'development') == 'production'
    return dict(
        httponly=True,
        secure=is_prod,
        samesite='Lax',
        max_age=7 * 24 * 3600,
        path='/api/auth',
    )

def _set_rt_cookie(resp, raw_token: str):
    resp.set_cookie('refreshToken', raw_token, **_cookie_kwargs())

def _clear_rt_cookie(resp):
    resp.delete_cookie('refreshToken', path='/api/auth')
