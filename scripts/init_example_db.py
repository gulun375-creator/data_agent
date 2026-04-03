"""Initialize the example SQLite database with sample data."""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/ecommerce.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北"]
CATEGORIES = ["电子产品", "服装", "食品", "家居", "图书"]

PRODUCTS = [
    ("iPhone 16", "电子产品", 7999.00),
    ("MacBook Pro", "电子产品", 14999.00),
    ("AirPods Pro", "电子产品", 1899.00),
    ("华为 Mate 70", "电子产品", 5999.00),
    ("小米电视", "电子产品", 3299.00),
    ("Nike 运动鞋", "服装", 899.00),
    ("优衣库外套", "服装", 499.00),
    ("Levi's 牛仔裤", "服装", 699.00),
    ("三只松鼠坚果", "食品", 89.00),
    ("良品铺子礼盒", "食品", 168.00),
    ("宜家书架", "家居", 599.00),
    ("戴森吸尘器", "家居", 4290.00),
    ("Python 编程", "图书", 79.00),
    ("数据分析实战", "图书", 69.00),
    ("AI 大模型", "图书", 99.00),
]

random.seed(42)


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            region TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            quantity INTEGER NOT NULL,
            status INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    base_date = datetime(2025, 7, 1)
    users = []
    for i in range(1, 201):
        name = f"用户{i:03d}"
        email = f"user{i:03d}@example.com"
        region = random.choice(REGIONS)
        days_ago = random.randint(0, 365)
        created = (base_date + timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        users.append((name, email, region, created))

    cur.executemany(
        "INSERT INTO users (name, email, region, created_at) VALUES (?, ?, ?, ?)",
        users,
    )

    product_rows = [(name, cat, price) for name, cat, price in PRODUCTS]
    cur.executemany(
        "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
        product_rows,
    )

    orders = []
    order_date_start = datetime(2026, 1, 1)
    order_date_end = datetime(2026, 4, 1)
    total_days = (order_date_end - order_date_start).days

    for _ in range(2000):
        user_id = random.randint(1, 200)
        product_idx = random.randint(0, len(PRODUCTS) - 1)
        product_id = product_idx + 1
        price = PRODUCTS[product_idx][2]
        quantity = random.randint(1, 5)
        total = round(price * quantity, 2)
        status = random.choices([0, 1, 2, 3, 4], weights=[5, 20, 15, 50, 10])[0]
        day_offset = random.randint(0, total_days - 1)
        hour = random.randint(8, 23)
        minute = random.randint(0, 59)
        created = (order_date_start + timedelta(days=day_offset, hours=hour, minutes=minute)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        orders.append((user_id, product_id, total, quantity, status, created))

    cur.executemany(
        "INSERT INTO orders (user_id, product_id, total_amount, quantity, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        orders,
    )

    conn.commit()

    print(f"数据库已创建: {DB_PATH}")
    print(f"  用户数: {cur.execute('SELECT COUNT(*) FROM users').fetchone()[0]}")
    print(f"  商品数: {cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]}")
    print(f"  订单数: {cur.execute('SELECT COUNT(*) FROM orders').fetchone()[0]}")

    conn.close()


if __name__ == "__main__":
    main()
