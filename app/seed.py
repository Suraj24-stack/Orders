import os
import random
from datetime import datetime, timedelta
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CREATE_TABLE = """
CREATE TABLE  orders (
    id          SERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    order_ref   TEXT UNIQUE NOT NULL,
    amount      NUMERIC(10, 2) NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('pending','completed','cancelled','expired')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CUSTOMERS = [
    "Alice Johnson", "Bob Smith", "Carol White", "David Brown",
    "Eva Martinez", "Frank Lee", "Grace Kim", "Henry Davis",
    "Iris Wilson", "James Taylor"
]
STATUSES = ["pending", "completed", "cancelled", "expired"]

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def seed():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE)
    cur.execute("TRUNCATE orders RESTART IDENTITY;")

    rows = []
    for i in range(1, 26):
        customer = random.choice(CUSTOMERS)
        order_ref = f"ORD-{i:04d}"
        amount = round(random.uniform(10.0, 500.0), 2)

        if i % 3 == 0:
            created_at = datetime.now() - timedelta(days=random.randint(31, 90))
        else:
            created_at = datetime.now() - timedelta(days=random.randint(0, 29))

        if i <= 8:
            status = "pending"
        elif i <= 13:
            status = "cancelled"
        elif i <= 18:
            status = "completed"
        else:
            status = random.choice(STATUSES)

        rows.append((customer, order_ref, amount, status, created_at))

    cur.executemany(
        "INSERT INTO orders (customer_name, order_ref, amount, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        rows
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f" Seeded {len(rows)} orders.")

if __name__ == "__main__":
    seed()
