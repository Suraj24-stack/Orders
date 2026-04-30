import os
import csv
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

load_dotenv()

EXPORT_PATH = "/exports/pending_orders.csv"

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def export_pending_to_csv(path=EXPORT_PATH):
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
    conn.close()
    print(f" Exported {len(rows)} pending orders → {path}")
    return rows

def expire_old_pending_orders():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE orders
        SET status = 'expired'
        WHERE status = 'pending'
          AND created_at < NOW() - INTERVAL '30 days'
        RETURNING id, order_ref, created_at;
    """)
    updated = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    print(f" Expired {len(updated)} old pending orders.")
    return updated

def delete_cancelled_orders():
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
    conn.close()
    print(f" Deleted {len(deleted)} cancelled orders.")
    return deleted

def show_status_counts():
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
    conn.close()
    print("\n Orders by Status:")
    print(f"  {'Status':<12} {'Count':>6}")
    print("  " + "-" * 20)
    for status, count in rows:
        print(f"  {status:<12} {count:>6}")
    return rows

if __name__ == "__main__":
    print("\n=== Step 1: Export pending orders ===")
    export_pending_to_csv()
    print("\n=== Step 2: Expire old pending orders ===")
    expire_old_pending_orders()
    print("\n=== Step 3: Delete cancelled orders ===")
    delete_cancelled_orders()
    print("\n=== Step 4: Status report ===")
    show_status_counts()
