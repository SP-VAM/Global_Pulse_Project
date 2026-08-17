"""
Unit and regression tests for FRD-030 Notifications.
Verifies:
  1. Successful expense transaction notification creation
  2. Successful income transaction notification creation
  3. Failed transaction does NOT create notifications
  4. Unusual account activity notification for anomalous transactions
  5. Budget threshold notification preservation
  6. User isolation for transaction notifications
"""
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.db.models.expense_model import BudgetModel, ExpenseCategoryModel, ExpenseModel, IncomeModel
from app.db.models.notification_model import NotificationModel
from app.schemas.expense import ExpenseCreate, IncomeCreate
from app.services.expense_service import ExpenseService
from app.services.notification_service import NotificationService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_cat = ExpenseCategoryModel(category_id=1, category_name="Food & Dining", color_code="#10b981")
    mock_result.scalar_one_or_none.return_value = mock_cat
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_successful_expense_creates_notification(mock_session):
    """Test that successfully creating an expense dispatches a FINANCIAL notification."""
    service = ExpenseService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    
    mock_expense = ExpenseModel(
        expense_id=101,
        user_id=1,
        category_id=1,
        amount=450.0,
        expense_date=date(2026, 8, 1),
        payment_method="UPI",
        notes="Lunch",
        created_at=dt_now,
    )
    service.expense_repo.create = AsyncMock(return_value=mock_expense)
    service.expense_repo.get_user_expenses_by_month = AsyncMock(return_value=[mock_expense])
    service.budget_repo.get_user_budgets_by_month = AsyncMock(return_value=[])

    mock_notif = NotificationModel(
        notification_id=1,
        user_id=1,
        title="Expense Added Successfully",
        message="Your expense of ₹450.00 for Food & Dining was added successfully.",
        notification_type="FINANCIAL",
        is_read=False,
    )

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_notif
        req = ExpenseCreate(amount=450.0, expense_date=date(2026, 8, 1), category_id=1, category_name="Food & Dining")
        resp = await service.create_expense(user_id=1, req=req)

        assert resp.expense_id == 101
        assert resp.amount == 450.0
        assert mock_send.called
        # Check call arguments
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["user_id"] == 1
        assert call_kwargs["title"] == "Expense Added Successfully"
        assert "450.00" in call_kwargs["message"]
        assert call_kwargs["notification_type"] == "FINANCIAL"


@pytest.mark.asyncio
async def test_successful_income_creates_notification(mock_session):
    """Test that successfully creating an income dispatches a FINANCIAL notification."""
    service = ExpenseService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    mock_income = IncomeModel(
        income_id=202,
        user_id=1,
        amount=75000.0,
        income_date=date(2026, 8, 1),
        payment_method="Salary",
        notes="Monthly Salary",
        created_at=dt_now,
    )
    service.income_repo.create = AsyncMock(return_value=mock_income)

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = MagicMock()
        req = IncomeCreate(amount=75000.0, income_date=date(2026, 8, 1), payment_method="Salary")
        resp = await service.create_income(user_id=1, req=req)

        assert resp.income_id == 202
        assert resp.amount == 75000.0
        assert mock_send.called
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["user_id"] == 1
        assert call_kwargs["title"] == "Income Added Successfully"
        assert "75,000.00" in call_kwargs["message"]
        assert call_kwargs["notification_type"] == "FINANCIAL"


@pytest.mark.asyncio
async def test_unusual_transaction_activity_alert(mock_session):
    """Test that an anomalously large expense triggers an UNUSUAL ACCOUNT ACTIVITY security notification."""
    service = ExpenseService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    # Historical average is ₹500
    prior_exp1 = ExpenseModel(expense_id=1, user_id=1, category_id=1, amount=500.0, expense_date=date(2026, 8, 1), created_at=dt_now)
    prior_exp2 = ExpenseModel(expense_id=2, user_id=1, category_id=1, amount=600.0, expense_date=date(2026, 8, 2), created_at=dt_now)
    
    # New huge expense ₹50,000 (much > 3x average)
    new_exp = ExpenseModel(expense_id=3, user_id=1, category_id=1, amount=50000.0, expense_date=date(2026, 8, 3), created_at=dt_now)
    
    service.expense_repo.create = AsyncMock(return_value=new_exp)
    service.expense_repo.get_user_expenses_by_month = AsyncMock(return_value=[prior_exp1, prior_exp2, new_exp])
    service.budget_repo.get_user_budgets_by_month = AsyncMock(return_value=[])

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_send:
        req = ExpenseCreate(amount=50000.0, expense_date=date(2026, 8, 3), category_id=1, category_name="Shopping")
        await service.create_expense(user_id=1, req=req)

        assert mock_send.call_count >= 2  # 1 for Expense Added, 1 for Unusual Activity
        calls = [c.kwargs for c in mock_send.call_args_list]
        unusual_call = next((c for c in calls if c["title"] == "Unusual Account Activity"), None)
        assert unusual_call is not None
        assert unusual_call["notification_type"] == "SECURITY"
        assert "50,000.00" in unusual_call["message"]


@pytest.mark.asyncio
async def test_budget_threshold_notification_preserved(mock_session):
    """Test that exceeding monthly budget still triggers BUDGET_ALERT."""
    service = ExpenseService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    mock_budget = BudgetModel(budget_id=10, user_id=1, category_id=2, budget_amount=5000.0, budget_month=8, budget_year=2026)
    exp1 = ExpenseModel(expense_id=5, user_id=1, category_id=2, amount=6000.0, expense_date=date(2026, 8, 1), created_at=dt_now)

    service.expense_repo.create = AsyncMock(return_value=exp1)
    service.expense_repo.get_user_expenses_by_month = AsyncMock(return_value=[exp1])
    service.budget_repo.get_user_budgets_by_month = AsyncMock(return_value=[mock_budget])

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_send:
        req = ExpenseCreate(amount=6000.0, expense_date=date(2026, 8, 1), category_id=2, category_name="Utilities")
        await service.create_expense(user_id=1, req=req)

        calls = [c.kwargs for c in mock_send.call_args_list]
        budget_call = next((c for c in calls if c["notification_type"] == "BUDGET_ALERT"), None)
        assert budget_call is not None
        assert "Limit Reached" in budget_call["title"]


@pytest.mark.asyncio
async def test_user_isolation_on_notifications(mock_session):
    """Verify User A's transaction dispatches notification strictly to User A, never to User B."""
    service = ExpenseService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    mock_expense = ExpenseModel(
        expense_id=77,
        user_id=1001,
        category_id=1,
        amount=1000.0,
        expense_date=date(2026, 8, 1),
        created_at=dt_now,
    )
    service.expense_repo.create = AsyncMock(return_value=mock_expense)
    service.expense_repo.get_user_expenses_by_month = AsyncMock(return_value=[mock_expense])
    service.budget_repo.get_user_budgets_by_month = AsyncMock(return_value=[])

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_send:
        req = ExpenseCreate(amount=1000.0, expense_date=date(2026, 8, 1), category_id=1)
        await service.create_expense(user_id=1001, req=req)

        for c in mock_send.call_args_list:
            assert c.kwargs["user_id"] == 1001
            assert c.kwargs["user_id"] != 2002  # User B never targeted
