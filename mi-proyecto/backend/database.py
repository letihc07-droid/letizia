# database.py — Base de datos SQLite
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'nexustech.db')


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         TEXT PRIMARY KEY,
            username   TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email      TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')),
            is_active  INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            revoked    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            ip         TEXT NOT NULL,
            success    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS products (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT NOT NULL,
            price       REAL NOT NULL CHECK(price > 0),
            old_price   REAL CHECK(old_price IS NULL OR old_price > 0),
            category    TEXT NOT NULL CHECK(category IN ('cpu','gpu','ram','storage','perifericos')),
            stock       INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            badge       TEXT CHECK(badge IS NULL OR badge IN ('new','sale')),
            icon        TEXT NOT NULL DEFAULT '📦',
            seller_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS orders (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            status     TEXT NOT NULL DEFAULT 'confirmed'
                           CHECK(status IN ('pending','confirmed','shipped','delivered','cancelled')),
            subtotal   REAL NOT NULL CHECK(subtotal >= 0),
            shipping   REAL NOT NULL DEFAULT 0,
            total      REAL NOT NULL CHECK(total >= 0),
            address    TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
            quantity   INTEGER NOT NULL CHECK(quantity > 0 AND quantity <= 99),
            unit_price REAL NOT NULL CHECK(unit_price > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_username   ON users(username);
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens   ON refresh_tokens(token_hash);
        CREATE INDEX IF NOT EXISTS idx_login_attempts   ON login_attempts(identifier, created_at);
        CREATE INDEX IF NOT EXISTS idx_products_cat     ON products(category, is_active);
        CREATE INDEX IF NOT EXISTS idx_orders_user      ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_order_items      ON order_items(order_id);
    """)
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada.")
