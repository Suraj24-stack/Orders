import os
import pytest
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("TEST_DATABASE_URL", os.environ.get("DATABASE_URL"))

from operations import (
    expire_old_pending_orders,
    delete_cancelled_orders,
    export_pending_to_csv,
)

@pytest.fixture(autouse=True)
def clean_db():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          SERIAL PRIMARY KEY,
            customer_name TEXT NOT NULL,
            order_ref   TEXT UNIQUE NOT NULL,
            amount      NUMERIC(10,2) NOT NULL,
            status      TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    cur.execute("TRUNCATE orders RESTART IDENTITY;")
    conn.commit()
    cur.close()
    conn.close()
    yield
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("TRUNCATE orders RESTART IDENTITY;")
    conn.commit()
    cur.close()
    conn.close()

def insert_order(customer, ref, amount, status, days_ago):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    created_at = datetime.now() - timedelta(days=days_ago)
    cur.execute(
        "INSERT INTO orders (customer_name, order_ref, amount, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (customer, ref, amount, status, created_at)
    )
    conn.commit()
    cur.close()
    conn.close()

def fetch_statuses():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT order_ref, status FROM orders ORDER BY order_ref;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {ref: status for ref, status in rows}

def test_old_pending_orders_become_expired():
    insert_order("Alice", "ORD-OLD", 100.0, "pending", days_ago=45)
    insert_order("Bob",   "ORD-NEW", 200.0, "pending", days_ago=5)
    expire_old_pending_orders()
    statuses = fetch_statuses()
    assert statuses["ORD-OLD"] == "expired"
    assert statuses["ORD-NEW"] == "pending"

def test_cancelled_orders_are_deleted():
    insert_order("Carol", "ORD-CANCEL", 50.0,  "cancelled", days_ago=2)
    insert_order("David", "ORD-KEEP",   150.0, "completed", days_ago=2)
    deleted = delete_cancelled_orders()
    statuses = fetch_statuses()
    assert "ORD-CANCEL" not in statuses
    assert "ORD-KEEP"   in  statuses
    assert len(deleted) == 1

def test_export_returns_only_pending(tmp_path):
    insert_order("Eve",   "ORD-P1",   80.0,  "pending",   days_ago=1)
    insert_order("Frank", "ORD-P2",   90.0,  "pending",   days_ago=2)
    insert_order("Grace", "ORD-DONE", 120.0, "completed", days_ago=1)
    path = str(tmp_path / "test_export.csv")
    rows = export_pending_to_csv(path=path)
    exported_refs = [r[2] for r in rows]
    assert "ORD-P1"   in exported_refs
    assert "ORD-P2"   in exported_refs
    assert "ORD-DONE" not in exported_refs
