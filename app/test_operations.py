"""Tests for data-cleaning operations."""
import os
import pytest
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
from operations import (
    expire_old_pending_orders,
    delete_cancelled_orders,
    export_pending_orders,
    get_conn,
)

load_dotenv()


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    order_ref VARCHAR(50) UNIQUE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture
def db_conn():
    """Provide a fresh DB connection with a clean orders table."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    cur.execute("TRUNCATE TABLE orders RESTART IDENTITY;")
    conn.commit()
    yield conn
    cur.execute("TRUNCATE TABLE orders RESTART IDENTITY;")
    conn.commit()
    cur.close()
    conn.close()


def insert_order(conn, customer, ref, amount, status, days_ago=0):
    cur = conn.cursor()
    created_at = datetime.now() - timedelta(days=days_ago)
    cur.execute(
        """INSERT INTO orders (customer_name, order_ref, amount, status, created_at)
           VALUES (%s, %s, %s, %s, %s)""",
        (customer, ref, amount, status, created_at)
    )
    conn.commit()
    cur.close()


def test_old_pending_orders_become_expired(db_conn):
    insert_order(db_conn, "Old Customer", "OLD-001", 1000, "pending", days_ago=45)
    insert_order(db_conn, "New Customer", "NEW-001", 2000, "pending", days_ago=10)

    updated = expire_old_pending_orders(days=30, conn=db_conn)

    cur = db_conn.cursor()
    cur.execute("SELECT order_ref, status FROM orders ORDER BY order_ref;")
    results = dict(cur.fetchall())

    assert len(updated) == 1
    assert results["OLD-001"] == "expired"
    assert results["NEW-001"] == "pending"


def test_cancelled_orders_are_deleted(db_conn):
    insert_order(db_conn, "A", "A-001", 100, "cancelled")
    insert_order(db_conn, "B", "B-001", 200, "cancelled")
    insert_order(db_conn, "C", "C-001", 300, "completed")

    deleted = delete_cancelled_orders(conn=db_conn)

    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders;")
    remaining = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status='cancelled';")
    cancelled_left = cur.fetchone()[0]

    assert len(deleted) == 2
    assert remaining == 1
    assert cancelled_left == 0


def test_export_returns_only_pending(db_conn, tmp_path):
    insert_order(db_conn, "P1", "P-001", 100, "pending")
    insert_order(db_conn, "P2", "P-002", 200, "pending")
    insert_order(db_conn, "C1", "C-001", 300, "completed")
    insert_order(db_conn, "X1", "X-001", 400, "cancelled")

    output_file = tmp_path / "test_pending.csv"
    rows = export_pending_orders(path=str(output_file), conn=db_conn)

    assert len(rows) == 2
    statuses = [row[4] for row in rows]
    assert all(s == "pending" for s in statuses)
    assert output_file.exists()