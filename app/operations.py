"""Data cleaning operations: export, update, delete, group counts."""
import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()

EXPORT_PATH = "/exports/pending_orders.csv"


def get_conn():
    """Get a database connection. Prefers DATABASE_URL, falls back to individual vars."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    # Fallback for environments that set individual vars
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "admin"),
        password=os.environ.get("POSTGRES_PASSWORD", "secret"),
        dbname=os.environ.get("POSTGRES_DB", "ordersdb"),
    )


def export_pending_to_csv(path=EXPORT_PATH, conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, customer_name, order_ref, amount, status, created_at
        FROM orders
        WHERE status = 'pending'
        ORDER BY created_at;
    """)
    rows = cur.fetchall()
    headers = ["id", "customer_name", "order_ref", "amount", "status", "created_at"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    cur.close()
    if own_conn:
        conn.close()
    print(f" Exported {len(rows)} pending orders → {path}")
    return rows


def expire_old_pending_orders(days=30, conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE orders
        SET status = 'expired'
        WHERE status = 'pending'
          AND created_at < NOW() - INTERVAL '{days} days'
        RETURNING id, order_ref, created_at;
    """)
    updated = cur.fetchall()
    conn.commit()
    cur.close()
    if own_conn:
        conn.close()
    print(f" Expired {len(updated)} old pending orders.")
    return updated


def delete_cancelled_orders(conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM orders
        WHERE status = 'cancelled'
        RETURNING id, order_ref;
    """)
    deleted = cur.fetchall()
    conn.commit()
    cur.close()
    if own_conn:
        conn.close()
    print(f" Deleted {len(deleted)} cancelled orders.")
    return deleted


def show_status_counts(conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT status, COUNT(*) AS total
        FROM orders
        GROUP BY status
        ORDER BY status;
    """)
    rows = cur.fetchall()
    cur.close()
    if own_conn:
        conn.close()
    print("\n Orders by Status:")
    print(f"  {'Status':<12} {'Count':>6}")
    print("  " + "-" * 20)
    for status, count in rows:
        print(f"  {status:<12} {count:>6}")
    return rows


# Backward compatibility alias for tests that use the old name
export_pending_orders = export_pending_to_csv


if __name__ == "__main__":
    print("\n=== Step 1: Export pending orders ===")
    export_pending_to_csv()
    print("\n=== Step 2: Expire old pending orders ===")
    expire_old_pending_orders()
    print("\n=== Step 3: Delete cancelled orders ===")
    delete_cancelled_orders()
    print("\n=== Step 4: Status report ===")
    show_status_counts()