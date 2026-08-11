"""
Unit tests for database session lifecycle and configuration.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_engine, get_db_session


@pytest.mark.asyncio
async def test_get_db_session_yields_session():
    """Verify that get_db_session yields a valid AsyncSession instance."""
    session_gen = get_db_session()
    session = await anext(session_gen)
    assert isinstance(session, AsyncSession)

    # Clean up generator
    try:
        await anext(session_gen)
    except StopAsyncIteration:
        pass


@pytest.mark.asyncio
async def test_async_engine_is_configured():
    """Verify that async_engine is initialized properly."""
    assert async_engine is not None
    assert async_engine.name in ("sqlite", "postgresql")
