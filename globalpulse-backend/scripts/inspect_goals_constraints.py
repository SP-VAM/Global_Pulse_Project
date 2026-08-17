import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_engine
from sqlalchemy import text

async def check():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'goals'::regclass;"))
        for row in res.fetchall():
            print("Constraint:", row[0], "->", row[1])

if __name__ == "__main__":
    asyncio.run(check())
