"""
GlobalPulse Database Session & Engine Configuration.

Configures async SQLAlchemy engine, session maker, connection pooling,
and FastAPI dependency injection for request-scoped sessions.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

db_url = settings.DATABASE_URL
if not db_url or "sqlite" in db_url.lower():
    raise RuntimeError(
        "Database Error: Application MUST connect to PostgreSQL database 'railway'. "
        "Silent fallback to SQLite is disabled. Please verify DATABASE_URL in .env."
    )

engine_kwargs = {
    "echo": False,
    "future": True,
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "pool_pre_ping": True,
}

async_engine: AsyncEngine = create_async_engine(db_url, **engine_kwargs)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a request-scoped AsyncSession.
    Automatically rolls back on uncaught exceptions and closes the session on completion.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
