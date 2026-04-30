"""Seed sample order data into Postgres."""
import os
import random
from datetime import datetime, timedelta
import psycopg2

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "user": os.getenv("POSTGRES_USER", "orders_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "orders_pass"),
    "dbname": os.getenv("POSTGRES_DB", "ordersdb"),
}

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    order_ref VARCHAR(50) UNIQUE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CUSTOMERS = [
    "Ram Sharma", "Sita Thapa", "Hari KC", "Gita Rai", "Bishnu Magar",
    "Kamala Gurung", "Suresh Adhikari", "Maya Tamang", "Krishna Shrestha",
    "Laxmi Poudel", "Dipak Lama", "Sabina Karki", "Manoj Basnet"
]
STATUSES = ["pending", "completed", "cancelled", "expired"]


def seed(num_rows=25):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Create table only if it doesn't exist
    cur.execute(CREATE_TABLE)

    # Wipe old data so we always seed a clean batch
    cur.execute("TRUNCATE TABLE orders RESTART IDENTITY;")

    # Build sample rows
    rows = []
    for i in range(1, num_rows + 1):
        customer = random.choice(CUSTOMERS)
        order_ref = f"ORD-2026-{i:04d}"
        amount = round(random.uniform(500, 50000), 2)
        status = random.choice(STATUSES)
        days_ago = random.randint(0, 90)
        created_at = datetime.now() - timedelta(days=days_ago)
        rows.append((customer, order_ref, amount, status, created_at))

    cur.executemany(
        """INSERT INTO orders (customer_name, order_ref, amount, status, created_at)
           VALUES (%s, %s, %s, %s, %s)""",
        rows
    )

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM orders;")
    count = cur.fetchone()[0]
    print(f"✅ Seeded {count} orders successfully.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    seed()