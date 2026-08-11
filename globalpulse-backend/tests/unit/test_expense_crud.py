import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.schemas.expense import ExpenseCreate, ExpenseUpdate, IncomeCreate, IncomeUpdate
from app.services.expense_service import ExpenseService
from app.db.models.expense_model import ExpenseModel, IncomeModel

@pytest.mark.asyncio
async def test_expense_crud_flow():
    mock_session = AsyncMock()
    service = ExpenseService(mock_session)

    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    mock_expense = ExpenseModel(
        expense_id=1,
        user_id=10,
        category_id=1,
        amount=100.0,
        expense_date=date(2026, 8, 1),
        payment_method="UPI",
        notes="Lunch",
        created_at=dt_now
    )

    service.expense_repo.create = AsyncMock(return_value=mock_expense)
    service.expense_repo.get_by_id = AsyncMock(return_value=mock_expense)
    service.expense_repo.update = AsyncMock(return_value=mock_expense)
    service.expense_repo.delete = AsyncMock(return_value=True)

    created = await service.create_expense(10, ExpenseCreate(category_id=1, amount=100.0, expense_date=date(2026,8,1), notes="Lunch"))
    assert created.expense_id == 1

    updated = await service.update_expense(10, 1, ExpenseUpdate(amount=150.0, notes="Dinner"))
    assert updated.expense_id == 1

    deleted = await service.delete_expense(10, 1)
    assert deleted is True

@pytest.mark.asyncio
async def test_income_crud_flow():
    mock_session = AsyncMock()
    service = ExpenseService(mock_session)

    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    mock_income = IncomeModel(
        income_id=1,
        user_id=10,
        amount=5000.0,
        income_date=date(2026, 8, 1),
        payment_method="Salary",
        notes="Bonus",
        created_at=dt_now
    )

    service.income_repo.create = AsyncMock(return_value=mock_income)
    service.income_repo.get_by_id = AsyncMock(return_value=mock_income)
    service.income_repo.update = AsyncMock(return_value=mock_income)
    service.income_repo.delete = AsyncMock(return_value=True)

    created = await service.create_income(10, IncomeCreate(amount=5000.0, income_date=date(2026,8,1), notes="Bonus"))
    assert created.income_id == 1

    updated = await service.update_income(10, 1, IncomeUpdate(amount=6000.0))
    assert updated.income_id == 1

    deleted = await service.delete_income(10, 1)
    assert deleted is True

@pytest.mark.asyncio
async def test_budget_crud_flow():
    mock_session = AsyncMock()
    service = ExpenseService(mock_session)

    service.budget_repo.get_by_id = AsyncMock(return_value=MagicMock(budget_id=1, user_id=10, category_id=1, budget_amount=500.0, budget_month=8, budget_year=2026))
    service.budget_repo.delete = AsyncMock(return_value=True)

    deleted = await service.delete_budget(10, 1)
    assert deleted is True
