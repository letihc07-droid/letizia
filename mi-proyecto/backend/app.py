# app.py — Punto de entrada Flask — NexusTech API
import os
from datetime import timedelta
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from dotenv import load_dotenv

from database import init_db
from routes.auth     import auth_bp
from routes.products import products_bp
from routes.orders   import orders_bp

load_dotenv()

JWT_SECRET     = os.getenv('JWT_SECRET')
JWT_REFRESH    = os.getenv('JWT_REFRESH_SECRET')
ALLOWED_ORIGIN = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8080')

if not JWT_SECRET or not JWT_REFRESH:
    raise RuntimeError(
        '\n❌ FATAL: Faltan JWT_SECRET y JWT_REFRESH_SECRET en el .env\n'
        'Genera valores con:\n'
        '  python -c "import secrets; print(secrets.token_hex(64))"\n'
    )


def create_app():
    app = Flask(__name__)

    # ── JWT ──────────────────────────────────────
    app.config['JWT_SECRET_KEY']           = JWT_SECRET
    app.config['JWT_ALGORITHM']            = 'HS256'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
    app.config['JWT_TOKEN_LOCATION']       = ['headers']
    app.config['JWT_HEADER_NAME']          = 'Authorization'
    app.config['JWT_HEADER_TYPE']          = 'Bearer'
    app.config['PROPAGATE_EXCEPTIONS']     = False

    JWTManager(app)

    # ── CORS ─────────────────────────────────────
    origins = [o.strip() for o in ALLOWED_ORIGIN.split(',')]
    for extra in ['http://localhost:8080', 'http://127.0.0.1:8080']:
        if extra not in origins:
            origins.append(extra)

    CORS(app,
         origins=origins,
         supports_credentials=True,
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization'],
    )

    # ── Rate limiting ─────────────────────────────
    Limiter(
        get_remote_address,
        app=app,
        default_limits=['300 per 15 minutes'],
        storage_uri='memory://',
    )

    # ── Cabeceras de seguridad ────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options']        = 'DENY'
        response.headers['X-XSS-Protection']       = '1; mode=block'
        response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control']          = 'no-store'
        response.headers.pop('Server', None)
        return response

    # ── Blueprints ───────────────────────────────
    app.register_blueprint(auth_bp,     url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(orders_bp,   url_prefix='/api/orders')

    # ── Health check ─────────────────────────────
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'version': '1.0'})

    # ── Error handlers ───────────────────────────
    @app.errorhandler(400)
    def bad_request(e):      return jsonify({'error': 'Petición incorrecta.'}), 400
    @app.errorhandler(401)
    def unauthorized(e):     return jsonify({'error': 'No autenticado.'}), 401
    @app.errorhandler(403)
    def forbidden(e):        return jsonify({'error': 'Acceso denegado.'}), 403
    @app.errorhandler(404)
    def not_found(e):        return jsonify({'error': 'Recurso no encontrado.'}), 404
    @app.errorhandler(405)
    def method_not_allowed(e): return jsonify({'error': 'Método no permitido.'}), 405
    @app.errorhandler(413)
    def too_large(e):        return jsonify({'error': 'Payload demasiado grande.'}), 413
    @app.errorhandler(429)
    def rate_limit(e):       return jsonify({'error': 'Demasiadas peticiones. Espera un momento.'}), 429
    @app.errorhandler(500)
    def server_error(e):
        print(f'[500] {e}')
        return jsonify({'error': 'Error interno del servidor.'}), 500

    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024  # 100 KB máximo por request

    return app


if __name__ == '__main__':
    init_db()
    app = create_app()
    port  = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    print(f'✅ NexusTech API en http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
