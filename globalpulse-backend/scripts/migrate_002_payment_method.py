"""
Direct DB migration script — safe to run multiple times.
Fixes the incomes_payment_method_check constraint.
"""
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("APP_ENV", "development")

from app.core.config import get_settings

settings = get_settings()
db_url = settings.DATABASE_URL
sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

import psycopg2

conn = psycopg2.connect(sync_url)
conn.autocommit = True
cur = conn.cursor()

# Safety check
cur.execute("""
    SELECT income_id, payment_method FROM incomes
    WHERE payment_method IS NOT NULL
      AND upper(payment_method) NOT IN ('CASH','CARD','UPI','NET_BANKING','WALLET','SALARY','OTHER')
""")
offending = cur.fetchall()
if offending:
    print("BLOCKED: offending rows:", offending)
    sys.exit(1)

print("Safety check passed — no offending income rows.")

# Drop existing constraint (idempotent)
cur.execute("ALTER TABLE incomes DROP CONSTRAINT IF EXISTS incomes_payment_method_check")
print("Old constraint dropped.")

# Create correct constraint
constraint_sql = """
ALTER TABLE incomes
ADD CONSTRAINT incomes_payment_method_check
CHECK (
    payment_method IS NULL
    OR upper(payment_method) = ANY (ARRAY['CASH','CARD','UPI','NET_BANKING','WALLET','SALARY','OTHER'])
)
"""
cur.execute(constraint_sql)
print("New constraint created.")

# Verify
cur.execute("""
    SELECT conname, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE conrelid = 'incomes'::regclass
      AND contype = 'c'
      AND conname = 'incomes_payment_method_check'
""")
row = cur.fetchone()
print("Verified:", row)

cur.close()
conn.close()
print("Migration 002 applied successfully.")
