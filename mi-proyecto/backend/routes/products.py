# routes/products.py — Productos: listar, crear, editar, borrar
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import get_connection
from security import sanitize_text, is_valid_uuid, new_uuid, safe_error

products_bp = Blueprint('products', __name__)

VALID_CATEGORIES = {'cpu', 'gpu', 'ram', 'storage', 'perifericos'}


# ════════════════════════════════════════════
# GET /api/products  — Listado público
# ════════════════════════════════════════════
@products_bp.route('/', methods=['GET'])
def list_products():
    try:
        page  = max(1, int(request.args.get('page', 1)))
        limit = max(1, min(100, int(request.args.get('limit', 20))))
    except (ValueError, TypeError):
        page, limit = 1, 20

    category = request.args.get('category', '').strip()
    search   = sanitize_text(request.args.get('search', ''), 100)
    offset   = (page - 1) * limit

    where  = ['p.is_active = 1']
    params = []

    if category and category != 'all' and category in VALID_CATEGORIES:
        where.append('p.category = ?')
        params.append(category)

    if search:
        where.append('(p.name LIKE ? OR p.description LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])

    where_sql = 'WHERE ' + ' AND '.join(where)
    conn = get_connection()
    try:
        total = conn.execute(
            f'SELECT COUNT(*) as n FROM products p {where_sql}', params
        ).fetchone()['n']

        rows = conn.execute(f"""
            SELECT p.id, p.name, p.description, p.price, p.old_price,
                   p.category, p.stock, p.badge, p.icon, p.created_at,
                   u.username AS seller_name
            FROM products p
            LEFT JOIN users u ON u.id = p.seller_id
            {where_sql}
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset]).fetchall()

        return jsonify({
            'data': [dict(r) for r in rows],
            'pagination': {
                'page': page, 'limit': limit,
                'total': total, 'pages': max(1, -(-total // limit)),
            }
        })
    finally:
        conn.close()


# ════════════════════════════════════════════
# GET /api/products/<id>
# ════════════════════════════════════════════
@products_bp.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    if not is_valid_uuid(product_id):
        return safe_error('ID de producto no válido.', 400)

    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT p.id, p.name, p.description, p.price, p.old_price,
                   p.category, p.stock, p.badge, p.icon, p.created_at,
                   u.username AS seller_name
            FROM products p
            LEFT JOIN users u ON u.id = p.seller_id
            WHERE p.id = ? AND p.is_active = 1
        """, (product_id,)).fetchone()

        if not row:
            return safe_error('Producto no encontrado.', 404)
        return jsonify({'data': dict(row)})
    finally:
        conn.close()


# ════════════════════════════════════════════
# POST /api/products  — Crear producto (auth)
# ════════════════════════════════════════════
@products_bp.route('/', methods=['POST'])
@jwt_required()
def create_product():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True)
    if not data:
        return safe_error('Body JSON requerido.', 400)

    errors = _validate_product(data)
    if errors:
        return jsonify({'error': 'Datos inválidos.', 'fields': errors}), 422

    conn = get_connection()
    try:
        product_id = new_uuid()
        conn.execute("""
            INSERT INTO products
              (id, name, description, price, old_price, category, stock, badge, icon, seller_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            sanitize_text(data['name'], 100),
            sanitize_text(data['description'], 500),
            round(float(data['price']), 2),
            round(float(data['old_price']), 2) if data.get('old_price') else None,
            data['category'],
            int(data.get('stock', 1)),
            data.get('badge') if data.get('badge') in ('new', 'sale') else None,
            sanitize_text(data.get('icon', '📦'), 10),
            user_id,
        ))
        conn.commit()
        row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        return jsonify({'message': 'Producto publicado.', 'data': dict(row)}), 201

    except Exception as e:
        conn.rollback()
        print(f'[create_product ERROR] {e}')
        return safe_error('Error interno del servidor.', 500)
    finally:
        conn.close()


# ════════════════════════════════════════════
# PUT /api/products/<id>  — Editar (dueño o admin)
# ════════════════════════════════════════════
@products_bp.route('/<product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    if not is_valid_uuid(product_id):
        return safe_error('ID no válido.', 400)

    user_id = get_jwt_identity()
    data    = request.get_json(silent=True)
    if not data:
        return safe_error('Body JSON requerido.', 400)

    conn = get_connection()
    try:
        product = conn.execute(
            'SELECT * FROM products WHERE id = ? AND is_active = 1', (product_id,)
        ).fetchone()
        if not product:
            return safe_error('Producto no encontrado.', 404)

        user = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
        if product['seller_id'] != user_id and (not user or user['role'] != 'admin'):
            return safe_error('No tienes permiso para editar este producto.', 403)

        errors = _validate_product(data)
        if errors:
            return jsonify({'error': 'Datos inválidos.', 'fields': errors}), 422

        conn.execute("""
            UPDATE products SET
                name = ?, description = ?, price = ?, old_price = ?,
                category = ?, stock = ?, badge = ?, icon = ?,
                created_at = created_at
            WHERE id = ?
        """, (
            sanitize_text(data['name'], 100),
            sanitize_text(data['description'], 500),
            round(float(data['price']), 2),
            round(float(data['old_price']), 2) if data.get('old_price') else None,
            data['category'],
            int(data.get('stock', 0)),
            data.get('badge') if data.get('badge') in ('new', 'sale') else None,
            sanitize_text(data.get('icon', product['icon']), 10),
            product_id,
        ))
        conn.commit()
        updated = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        return jsonify({'message': 'Producto actualizado.', 'data': dict(updated)})

    except Exception as e:
        conn.rollback()
        print(f'[update_product ERROR] {e}')
        return safe_error('Error interno del servidor.', 500)
    finally:
        conn.close()


# ════════════════════════════════════════════
# DELETE /api/products/<id>  — Borrado lógico
# ════════════════════════════════════════════
@products_bp.route('/<product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    if not is_valid_uuid(product_id):
        return safe_error('ID no válido.', 400)

    user_id = get_jwt_identity()
    conn = get_connection()
    try:
        product = conn.execute(
            'SELECT seller_id FROM products WHERE id = ? AND is_active = 1', (product_id,)
        ).fetchone()
        if not product:
            return safe_error('Producto no encontrado.', 404)

        user = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
        if product['seller_id'] != user_id and (not user or user['role'] != 'admin'):
            return safe_error('No tienes permiso para eliminar este producto.', 403)

        conn.execute('UPDATE products SET is_active = 0 WHERE id = ?', (product_id,))
        conn.commit()
        return jsonify({'message': 'Producto eliminado.'})
    finally:
        conn.close()


# ── Validación interna ────────────────────────────────────────

def _validate_product(data: dict) -> dict:
    errors = {}
    name = sanitize_text(data.get('name', ''), 100)
    if not name or len(name) < 2:
        errors['name'] = 'Nombre: mínimo 2 caracteres.'

    desc = sanitize_text(data.get('description', ''), 500)
    if not desc or len(desc) < 5:
        errors['description'] = 'Descripción: mínimo 5 caracteres.'

    try:
        price = float(data.get('price', 0))
        if price <= 0 or price > 999999:
            raise ValueError
    except (ValueError, TypeError):
        errors['price'] = 'Precio: número positivo obligatorio.'

    if data.get('category') not in VALID_CATEGORIES:
        errors['category'] = 'Categoría no válida.'

    try:
        stock = int(data.get('stock', 0))
        if stock < 0 or stock > 9999:
            raise ValueError
    except (ValueError, TypeError):
        errors['stock'] = 'Stock: entero entre 0 y 9999.'

    return errors
