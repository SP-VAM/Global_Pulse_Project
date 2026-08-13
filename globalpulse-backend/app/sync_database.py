import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import get_settings

settings = get_settings()
raw_url = settings.DATABASE_URL or os.getenv("DATABASE_URL", "")
if not raw_url or "sqlite" in raw_url.lower():
    raise RuntimeError(
        "Sync Database Error: DATABASE_URL must be configured with PostgreSQL database 'railway'. "
        "SQLite is not permitted for application persistence."
    )

if "+asyncpg" in raw_url:
    raw_url = raw_url.replace("+asyncpg", "")

engine = create_engine(
    raw_url,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()