"""
Test all supported payment methods for income creation against the live Railway PostgreSQL.
Inserts test rows, verifies acceptance, then removes them.
Also tests that an unsupported value is rejected.
"""
import os, sys, datetime
sys.path.insert(0, ".")
os.environ.setdefault("APP_ENV", "development")

from app.core.config import get_settings
settings = get_settings()
sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

import psycopg2

conn = psycopg2.connect(sync_url)
conn.autocommit = False
cur = conn.cursor()

# Get a real user_id for the test
cur.execute("SELECT user_id FROM users LIMIT 1")
row = cur.fetchone()
if not row:
    print("No users found — cannot run test.")
    sys.exit(1)

test_user_id = row[0]
today = datetime.date.today()
inserted_ids = []

ALLOWED = ["CASH", "CARD", "UPI", "NET_BANKING", "WALLET", "SALARY", "OTHER"]

print(f"Testing with user_id={test_user_id}")

# Test each allowed method
for pm in ALLOWED:
    try:
        cur.execute(
            "INSERT INTO incomes (user_id, amount, income_date, payment_method, notes) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING income_id",
            (test_user_id, 1.00, today, pm, f"MIGRATION TEST - {pm}")
        )
        iid = cur.fetchone()[0]
        inserted_ids.append(iid)
        conn.commit()
        print(f"  PASS: {pm} accepted (income_id={iid})")
    except Exception as e:
        conn.rollback()
        print(f"  FAIL: {pm} rejected — {e}")

# Test an unsupported method — must be rejected
try:
    cur.execute(
        "INSERT INTO incomes (user_id, amount, income_date, payment_method, notes) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING income_id",
        (test_user_id, 1.00, today, "BANK_TRANSFER", "MIGRATION TEST - INVALID")
    )
    conn.commit()
    print("  FAIL: BANK_TRANSFER should have been rejected but was accepted!")
except Exception as e:
    conn.rollback()
    print(f"  PASS: BANK_TRANSFER correctly rejected — {e}")

# Cleanup test rows
if inserted_ids:
    cur.execute(
        "DELETE FROM incomes WHERE income_id = ANY(%s) AND notes LIKE %s",
        (inserted_ids, "MIGRATION TEST%")
    )
    conn.commit()
    print(f"\nCleaned up {len(inserted_ids)} test rows.")

cur.close()
conn.close()
print("\nAll payment method tests complete.")
