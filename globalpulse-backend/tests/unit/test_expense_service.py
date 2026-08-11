"""
Unit and integration tests for ExpenseService and Expense Tracker APIs.
"""
from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.repositories.user_repository import UserRepository
from app.schemas.expense import BudgetCreate, ExpenseCreate, IncomeCreate
from app.services.expense_service import ExpenseService

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_expense_service_flow():
    async with TestSessionLocal() as db_session:
        # 1. Create test user
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            {
                "username": "exp_user",
                "email": "exp@globalpulse.io",
                "mobile_number": "+919988776655",
                "password_hash": "hashed_pw",
                "auth_provider": "LOCAL",
                "is_mobile_verified": True,
                "account_status": "ACTIVE",
            }
        )

        service = ExpenseService(db_session)

        # 2. Record Income
        inc = await service.create_income(
            user.user_id,
            IncomeCreate(amount=50000.0, income_date=date(2026, 7, 1), payment_method="Salary", notes="Monthly Salary"),
        )
        assert inc.amount == 50000.0

        # 3. Record Expense
        exp = await service.create_expense(
            user.user_id,
            ExpenseCreate(category_name="Food", amount=1500.0, expense_date=date(2026, 7, 2), payment_method="UPI", notes="Dinner"),
        )
        assert exp.amount == 1500.0

        # 4. Save Budget
        budget = await service.save_budget(
            user.user_id,
            BudgetCreate(category_name="Food", budget_amount=5000.0, budget_month=7, budget_year=2026),
        )
        assert budget.budget_amount == 5000.0

        # 5. Verify Monthly Summary
        summary = await service.get_monthly_summary(user.user_id, 2026, 7)
        assert summary.monthly_income == 50000.0
        assert summary.monthly_spending == 1500.0
        assert summary.savings == 48500.0
        assert len(summary.expenses) == 1
        assert len(summary.incomes) == 1
        assert len(summary.budgets) == 1
