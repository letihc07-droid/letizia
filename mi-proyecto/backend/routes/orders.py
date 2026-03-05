# routes/orders.py — Pedidos con precios calculados en backend y protección IDOR
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import get_connection
from security import sanitize_text, is_valid_uuid, is_valid_zip, new_uuid, safe_error

orders_bp = Blueprint('orders', __name__)


# ════════════════════════════════════════════
# POST /api/orders  — Crear pedido
# ════════════════════════════════════════════
@orders_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    user_id = get_jwt_identity()
    data    = request.get_json(silent=True)
    if not data:
        return safe_error('Body JSON requerido.', 400)

    items   = data.get('items', [])
    address = data.get('address', {})

    # Validar estructura básica
    if not isinstance(items, list) or len(items) == 0:
        return safe_error('El pedido debe tener al menos 1 producto.', 422)
    if len(items) > 50:
        return safe_error('Máximo 50 productos por pedido.', 422)

    # Validar cada línea
    for i, item in enumerate(items):
        if not is_valid_uuid(str(item.get('product_id', ''))):
            return safe_error(f'ID de producto inválido en línea {i+1}.', 400)
        try:
            qty = int(item.get('quantity', 0))
            if qty < 1 or qty > 99:
                raise ValueError
        except (ValueError, TypeError):
            return safe_error(f'Cantidad inválida en línea {i+1} (1–99).', 400)

    # Validar dirección
    addr_errors = _validate_address(address)
    if addr_errors:
        return jsonify({'error': 'Dirección inválida.', 'fields': addr_errors}), 422

    conn = get_connection()
    try:
        # Obtener productos de BD — NUNCA confiar en precios del frontend
        ids          = [item['product_id'] for item in items]
        placeholders = ','.join('?' * len(ids))
        db_products  = conn.execute(
            f'SELECT id, name, price, stock, is_active FROM products WHERE id IN ({placeholders})',
            ids
        ).fetchall()
        product_map = {p['id']: dict(p) for p in db_products}

        # Verificar stock y existencia
        for item in items:
            p = product_map.get(item['product_id'])
            if not p or not p['is_active']:
                return safe_error(f'Producto no disponible.', 404)
            if p['stock'] < int(item['quantity']):
                return safe_error(f'Stock insuficiente para "{p["name"]}". Solo quedan {p["stock"]}.', 409)

        # Calcular precios en backend
        subtotal = round(sum(
            product_map[i['product_id']]['price'] * int(i['quantity'])
            for i in items
        ), 2)
        shipping = 0.0 if subtotal >= 500 else 9.99
        total    = round(subtotal + shipping, 2)

        safe_address = {
            'street':  sanitize_text(address.get('street', ''), 200),
            'city':    sanitize_text(address.get('city', ''), 100),
            'zip':     sanitize_text(address.get('zip', ''), 10),
            'country': sanitize_text(address.get('country', 'España'), 60),
        }

        # Transacción atómica: pedido + líneas + stock
        order_id = new_uuid()
        conn.execute("""
            INSERT INTO orders (id, user_id, subtotal, shipping, total, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, subtotal, shipping, total, json.dumps(safe_address)))

        for item in items:
            conn.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            """, (
                order_id,
                item['product_id'],
                int(item['quantity']),
                product_map[item['product_id']]['price'],
            ))
            conn.execute(
                'UPDATE products SET stock = stock - ? WHERE id = ?',
                (int(item['quantity']), item['product_id'])
            )

        conn.commit()
        return jsonify({
            'message': 'Pedido confirmado.',
            'data': {
                'order_id': order_id,
                'subtotal': subtotal,
                'shipping': shipping,
                'total':    total,
            },
        }), 201

    except Exception as e:
        conn.rollback()
        print(f'[create_order ERROR] {e}')
        return safe_error('Error interno del servidor.', 500)
    finally:
        conn.close()


# ════════════════════════════════════════════
# GET /api/orders  — Mis pedidos
# ════════════════════════════════════════════
@orders_bp.route('/', methods=['GET'])
@jwt_required()
def list_orders():
    user_id = get_jwt_identity()
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, status, subtotal, shipping, total, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,)).fetchall()
        return jsonify({'data': [dict(r) for r in rows]})
    finally:
        conn.close()


# ════════════════════════════════════════════
# GET /api/orders/<id>  — Detalle (IDOR protegido)
# ════════════════════════════════════════════
@orders_bp.route('/<order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    if not is_valid_uuid(order_id):
        return safe_error('ID no válido.', 400)

    user_id = get_jwt_identity()
    conn = get_connection()
    try:
        # Filtramos por id Y user_id → imposible ver pedidos ajenos
        order = conn.execute("""
            SELECT id, status, subtotal, shipping, total, address, created_at
            FROM orders
            WHERE id = ? AND user_id = ?
        """, (order_id, user_id)).fetchone()

        if not order:
            return safe_error('Pedido no encontrado.', 404)

        items = conn.execute("""
            SELECT oi.quantity, oi.unit_price, p.name, p.category, p.icon
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()

        order_dict            = dict(order)
        order_dict['address'] = json.loads(order_dict['address'])
        order_dict['items']   = [dict(i) for i in items]
        return jsonify({'data': order_dict})
    finally:
        conn.close()


# ── Validación de dirección ───────────────────────────────────
def _validate_address(addr: dict) -> dict:
    errors = {}
    if not addr.get('street') or len(str(addr['street']).strip()) < 3:
        errors['street'] = 'Calle requerida.'
    if not addr.get('city') or len(str(addr['city']).strip()) < 2:
        errors['city'] = 'Ciudad requerida.'
    if not is_valid_zip(str(addr.get('zip', ''))):
        errors['zip'] = 'Código postal: 5 dígitos.'
    return errors
