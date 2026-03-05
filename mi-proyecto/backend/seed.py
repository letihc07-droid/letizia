# seed.py — Inserta los 12 productos iniciales
# Ejecutar UNA SOLA VEZ después de levantar Docker:
#   docker-compose exec api python seed.py

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from database import get_connection, init_db
from security import new_uuid

PRODUCTS = [
    {'name': 'Intel Core i9-14900K',         'description': '24 núcleos (8P+16E), hasta 6.0 GHz, socket LGA1700',  'price': 589.99, 'old_price': 649.99, 'category': 'cpu',        'stock': 8,  'badge': 'sale', 'icon': '🔲'},
    {'name': 'AMD Ryzen 9 7950X',             'description': '16 núcleos / 32 hilos, hasta 5.7 GHz, socket AM5',    'price': 549.99, 'old_price': None,   'category': 'cpu',        'stock': 5,  'badge': 'new',  'icon': '🔲'},
    {'name': 'AMD Ryzen 5 7600X',             'description': '6 núcleos / 12 hilos, hasta 5.3 GHz, socket AM5',     'price': 239.99, 'old_price': None,   'category': 'cpu',        'stock': 30, 'badge': None,   'icon': '🔲'},
    {'name': 'RTX 4090 24GB GDDR6X',          'description': 'DLSS 3, Ray Tracing, 16384 CUDA cores',               'price': 1799.99,'old_price':1999.99, 'category': 'gpu',        'stock': 3,  'badge': 'sale', 'icon': '🖥️'},
    {'name': 'RX 7900 XTX 24GB',              'description': 'RDNA3, DisplayPort 2.1, 96 Compute Units',            'price': 999.99, 'old_price': None,   'category': 'gpu',        'stock': 6,  'badge': None,   'icon': '🖥️'},
    {'name': 'Corsair 32GB DDR5-6000',         'description': 'Dual channel, XMP 3.0, CL30',                        'price': 129.99, 'old_price': None,   'category': 'ram',        'stock': 20, 'badge': None,   'icon': '💾'},
    {'name': 'G.Skill Trident Z5 64GB',        'description': 'DDR5-6400, RGB, XMP 3.0, CL32',                      'price': 249.99, 'old_price': None,   'category': 'ram',        'stock': 12, 'badge': 'new',  'icon': '💾'},
    {'name': 'Samsung 990 Pro 2TB',            'description': 'NVMe PCIe 4.0, 7450/6900 MB/s lectura/escritura',   'price': 189.99, 'old_price': 219.99, 'category': 'storage',    'stock': 15, 'badge': 'sale', 'icon': '💿'},
    {'name': 'WD Black SN850X 4TB',            'description': 'PCIe 4.0, 7300 MB/s lectura, compatible PS5',        'price': 299.99, 'old_price': None,   'category': 'storage',    'stock': 9,  'badge': None,   'icon': '💿'},
    {'name': 'Logitech G Pro X Superlight 2',  'description': 'Inalámbrico, 32K DPI, 60h batería, solo 60g',        'price': 159.99, 'old_price': None,   'category': 'perifericos','stock': 25, 'badge': 'new',  'icon': '🖱️'},
    {'name': 'Keychron Q3 Max',                'description': 'TKL, QMK/VIA, Gateron G Pro, carcasa aluminio',      'price': 199.99, 'old_price': None,   'category': 'perifericos','stock': 18, 'badge': None,   'icon': '⌨️'},
    {'name': 'ASUS ROG Swift OLED 4K 27"',     'description': '4K OLED, 240Hz, 0.03ms, HDMI 2.1',                  'price': 699.99, 'old_price': 799.99, 'category': 'perifericos','stock': 7,  'badge': 'sale', 'icon': '🖥️'},
]

def seed():
    init_db()
    conn = get_connection()
    existing = conn.execute('SELECT COUNT(*) as n FROM products').fetchone()['n']
    if existing > 0:
        print(f'⚠️  Ya hay {existing} productos. No se insertan duplicados.')
        conn.close()
        return
    for p in PRODUCTS:
        conn.execute("""
            INSERT INTO products (id, name, description, price, old_price, category, stock, badge, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_uuid(), p['name'], p['description'], p['price'], p['old_price'],
              p['category'], p['stock'], p['badge'], p['icon']))
    conn.commit()
    conn.close()
    print(f'✅ {len(PRODUCTS)} productos insertados.')

if __name__ == '__main__':
    seed()
