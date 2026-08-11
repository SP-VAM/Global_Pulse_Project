"""
Unit and integration tests for Generic BaseRepository and Module Repositories.
Uses an isolated in-memory SQLite async engine.
"""
from datetime import date, datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import DuplicateRecordError
from app.db.models import Base, GoalModel, UserModel
from app.repositories.base import BaseRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.user_repository import UserRepository

# Isolated test engine
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create all ORM tables in the in-memory test database before each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Yield a transactional test session."""
    async with TestSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_user_repository_crud(db_session: AsyncSession):
    """Test UserRepository create, lookup by email, and count."""
    user_repo = UserRepository(db_session)

    user_data = {
        "username": "testuser",
        "email": "test@globalpulse.io",
        "password_hash": "hashed_pw",
        "auth_provider": "LOCAL",
    }

    user = await user_repo.create(user_data)
    assert user.user_id is not None
    assert user.username == "testuser"

    fetched = await user_repo.get_by_email("test@globalpulse.io")
    assert fetched is not None
    assert fetched.user_id == user.user_id

    total = await user_repo.count()
    assert total == 1


@pytest.mark.asyncio
async def test_user_repository_duplicate_email_raises_exception(db_session: AsyncSession):
    """Test that creating a user with a duplicate email raises DuplicateInstrumentError."""
    user_repo = UserRepository(db_session)

    user_data = {"username": "user1", "email": "duplicate@globalpulse.io"}
    await user_repo.create(user_data)

    user_data_dup = {"username": "user2", "email": "duplicate@globalpulse.io"}
    with pytest.raises(DuplicateRecordError):
        await user_repo.create(user_data_dup)


@pytest.mark.asyncio
async def test_goal_repository_operations(db_session: AsyncSession):
    """Test GoalRepository active goal queries and soft delete."""
    user_repo = UserRepository(db_session)
    goal_repo = GoalRepository(db_session)

    user = await user_repo.create({"username": "goaluser", "email": "goal@globalpulse.io"})

    # Create goal
    goal = await goal_repo.create(
        {
            "user_id": user.user_id,
            "investment_type_id": 1,
            "status_id": 1,
            "goal_name": "Buy House",
            "target_quantity": 500000.0,
            "current_quantity": 100000.0,
            "unit": "INR",
            "start_date": date(2026, 1, 1),
            "end_date": date(2030, 1, 1),
        }
    )

    active_goals = await goal_repo.get_active_goals_by_user(user.user_id)
    assert len(active_goals) == 1
    assert active_goals[0].goal_name == "Buy House"

    count = await goal_repo.get_active_count(user.user_id)
    assert count == 1

    # Soft delete
    deleted = await goal_repo.soft_delete(goal.goal_id, user.user_id)
    assert deleted is True

    count_after = await goal_repo.get_active_count(user.user_id)
    assert count_after == 0
