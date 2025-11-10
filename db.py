# CLEAN FILE HEADER (DO NOT REMOVE)
# db.py — SQLite helpers for Orders Portal
# UTF-8

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = "db.sqlite"

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as con:
        cur = con.cursor()
        # customers
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            name TEXT,
            type TEXT,
            phone TEXT,
            email TEXT,
            location TEXT,
            contract_end_date TEXT,
            market_share_percent REAL
        )
        """)
        # products
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            section TEXT,
            analyser TEXT,
            kit_size TEXT,
            default_price_usd REAL
        )
        """)
        # fixed prices
        cur.execute("""
        CREATE TABLE IF NOT EXISTS fixed_prices(
            customer_id INTEGER,
            product_id INTEGER,
            price_usd REAL,
            PRIMARY KEY(customer_id, product_id)
        )
        """)
        # orders
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            status TEXT,
            pr_number TEXT,
            created_at TEXT
        )
        """)
        # order lines
        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_lines(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            qty INTEGER
        )
        """)
        # announcements
        cur.execute("""
        CREATE TABLE IF NOT EXISTS announcements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            body TEXT,
            is_active INTEGER,
            created_at TEXT
        )
        """)

        # seed admin
        cur.execute("SELECT COUNT(*) FROM customers WHERE username='admin'",)
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO customers(username, password, name, type, email)
                VALUES('admin','admin','Administrator','Direct','admin@example.com')
            """)

# ---------------- Auth ----------------
def auth_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    with get_conn() as con:
        row = con.execute(
            "SELECT * FROM customers WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["role"] = "admin" if username == "admin" else "customer"
        return d

# ---------------- Products ----------------
def upsert_product(code: str, name: str, section: str, analyser: str, kit_size: str, default_price_usd: float):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT id FROM products WHERE code=?", (code,))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE products SET name=?, section=?, analyser=?, kit_size=?, default_price_usd=?
                WHERE code=?
            """, (name, section, analyser, kit_size, float(default_price_usd), code))
        else:
            cur.execute("""
                INSERT INTO products(code,name,section,analyser,kit_size,default_price_usd)
                VALUES(?,?,?,?,?,?)
            """, (code, name, section, analyser, kit_size, float(default_price_usd)))

def list_products() -> List[Dict[str, Any]]:
    with get_conn() as con:
        rows = con.execute("""
            SELECT id, code, name, section, analyser, kit_size, default_price_usd
            FROM products ORDER BY name
        """).fetchall()
        return [dict(r) for r in rows]

def delete_product(code: str):
    with get_conn() as con:
        con.execute("DELETE FROM products WHERE code=?", (code,))

# ---------------- Fixed prices ----------------
def set_fixed_price(customer_id: int, product_id: int, price_usd: float):
    with get_conn() as con:
        con.execute("""
            INSERT INTO fixed_prices(customer_id, product_id, price_usd)
            VALUES(?,?,?)
            ON CONFLICT(customer_id, product_id) DO UPDATE SET price_usd=excluded.price_usd
        """, (int(customer_id), int(product_id), float(price_usd)))

def get_price_for_customer_product(customer_id: int, product_id: int) -> Optional[float]:
    with get_conn() as con:
        row = con.execute("""
            SELECT price_usd FROM fixed_prices
            WHERE customer_id=? AND product_id=?
        """, (int(customer_id), int(product_id))).fetchone()
        return float(row["price_usd"]) if row else None

# ---------------- Orders ----------------
def add_order(customer_id: int, status: str = "Draft") -> int:
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO orders(customer_id, status, pr_number, created_at)
            VALUES(?,?,?,?)
        """, (int(customer_id), status, None, datetime.utcnow().isoformat()))
        return cur.lastrowid

def add_order_line(order_id: int, product_id: int, qty: int):
    with get_conn() as con:
        con.execute("""
            INSERT INTO order_lines(order_id, product_id, qty)
            VALUES(?,?,?)
        """, (int(order_id), int(product_id), int(qty)))

def update_order_status(order_id: int, status: str, pr_number: Optional[str] = None):
    with get_conn() as con:
        if pr_number is None:
            con.execute("UPDATE orders SET status=? WHERE id=?", (status, int(order_id)))
        else:
            con.execute("UPDATE orders SET status=?, pr_number=? WHERE id=?", (status, pr_number, int(order_id)))

def delete_order(order_id: int):
    with get_conn() as con:
        con.execute("DELETE FROM order_lines WHERE order_id=?", (int(order_id),))
        con.execute("DELETE FROM orders WHERE id=?", (int(order_id),))

def list_orders(customer_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_conn() as con:
        if customer_id is None:
            rows = con.execute("""
                SELECT id, customer_id, status, pr_number, created_at
                FROM orders ORDER BY created_at DESC
            """).fetchall()
        else:
            rows = con.execute("""
                SELECT id, customer_id, status, pr_number, created_at
                FROM orders WHERE customer_id=? ORDER BY created_at DESC
            """, (int(customer_id),)).fetchall()
        return [dict(r) for r in rows]

def list_order_lines(order_id: int) -> List[Dict[str, Any]]:
    with get_conn() as con:
        rows = con.execute("""
            SELECT id, order_id, product_id, qty
            FROM order_lines WHERE order_id=?
        """, (int(order_id),)).fetchall()
        return [dict(r) for r in rows]

# ---------------- Customers ----------------
def list_customers_full() -> List[Dict[str, Any]]:
    with get_conn() as con:
        rows = con.execute("""
            SELECT id, username, name, type, phone, email, location, contract_end_date, market_share_percent
            FROM customers
            ORDER BY COALESCE(name, username)
        """).fetchall()
        return [dict(r) for r in rows]

def create_customer(
    username: str,
    password: str,
    name: str,
    cust_type: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    location: Optional[str] = None,
    contract_end_date: Optional[str] = None,
    market_share_percent: Optional[float] = None,
):
    with get_conn() as con:
        con.execute("""
            INSERT INTO customers(username,password,name,type,phone,email,location,contract_end_date,market_share_percent)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (username, password, name, cust_type, phone, email, location, contract_end_date, market_share_percent))

def update_customer(
    customer_id: int,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    cust_type: Optional[str] = None,
    location: Optional[str] = None,
    contract_end_date: Optional[str] = None,
    market_share_percent: Optional[float] = None,
):
    fields = []
    vals: List[Any] = []
    if name is not None:
        fields.append("name=?"); vals.append(name)
    if phone is not None:
        fields.append("phone=?"); vals.append(phone)
    if email is not None:
        fields.append("email=?"); vals.append(email)
    if username is not None:
        fields.append("username=?"); vals.append(username)
    if cust_type is not None:
        fields.append("type=?"); vals.append(cust_type)
    if location is not None:
        fields.append("location=?"); vals.append(location)
    if contract_end_date is not None:
        fields.append("contract_end_date=?"); vals.append(contract_end_date)
    if market_share_percent is not None:
        fields.append("market_share_percent=?"); vals.append(market_share_percent)
    if not fields:
        return
    vals.append(int(customer_id))
    with get_conn() as con:
        con.execute(f"UPDATE customers SET {', '.join(fields)} WHERE id=?", vals)

# ---------------- Announcements ----------------
def create_announcement(title: str, body: str):
    with get_conn() as con:
        con.execute("""
            INSERT INTO announcements(title, body, is_active, created_at)
            VALUES(?,?,1,?)
        """, (title, body, datetime.utcnow().isoformat()))

def get_active_announcements() -> List[Dict[str, Any]]:
    with get_conn() as con:
        rows = con.execute("""
            SELECT id, title, body, created_at FROM announcements
            WHERE is_active=1 ORDER BY created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

def deactivate_announcement(announcement_id: int):
    with get_conn() as con:
        con.execute("UPDATE announcements SET is_active=0 WHERE id=?", (int(announcement_id),))
