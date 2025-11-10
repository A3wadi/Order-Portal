import sqlite3
from datetime import datetime

DB_NAME = "orders.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        analyzer TEXT,
        kit_size REAL,
        price REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        product_id INTEGER,
        quantity INTEGER,
        status TEXT,
        created_at TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        active INTEGER DEFAULT 1
    )
    """)

    # إنشاء مستخدم الأدمن الافتراضي
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', '1234', 'admin')")

    conn.commit()
    conn.close()

def auth_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def add_order(customer, product_id, quantity):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO orders (customer, product_id, quantity, status, created_at) VALUES (?, ?, ?, 'Submitted', ?)",
              (customer, product_id, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def list_orders():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT o.id, o.customer, p.name, o.quantity, o.status, o.created_at FROM orders o LEFT JOIN products p ON o.product_id=p.id")
    rows = c.fetchall()
    conn.close()
    return rows

def list_products():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    rows = c.fetchall()
    conn.close()
    return rows

def add_product(name, analyzer, kit_size, price):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO products (name, analyzer, kit_size, price) VALUES (?, ?, ?, ?)", (name, analyzer, kit_size, price))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
