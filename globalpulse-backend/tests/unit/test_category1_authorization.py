"""
Category 1: Authorization & User Isolation Tests — Backend Hardening Phase 2

Validates that:
- User A cannot modify or delete User B's expenses, incomes, budgets, or portfolio investments.
- JWT tokens encode the correct user identity — no leakage.
- All cross-user mutations raise ValidationError.
- Legitimate owners are never blocked.

Pattern: mocked AsyncSession — no live DB required.
"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone

USER_A_ID = 101
USER_B_ID = 202
dt_now = datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc)


def make_mock_expense(expense_id, user_id):
    m = MagicMock()
    m.expense_id = expense_id
    m.user_id = user_id
    m.amount = 150.0
    m.expense_date = date(2026, 8, 6)
    m.payment_method = "UPI"
    m.notes = "Private"
    m.created_at = dt_now
    m.category_id = 1
    return m


def make_mock_income(income_id, user_id):
    m = MagicMock()
    m.income_id = income_id
    m.user_id = user_id
    m.amount = 5000.0
    m.income_date = date(2026, 8, 1)
    m.payment_method = "Salary"
    m.notes = "Monthly"
    m.created_at = dt_now
    return m


def make_mock_budget(budget_id, user_id):
    m = MagicMock()
    m.budget_id = budget_id
    m.user_id = user_id
    m.category_id = 1
    m.budget_amount = 1000.0
    m.budget_month = 8
    m.budget_year = 2026
    m.created_at = dt_now
    return m


def make_mock_investment(investment_id, user_id):
    m = MagicMock()
    m.investment_id = investment_id
    m.user_id = user_id
    m.asset_type = "EQUITY"
    m.ticker = "RELIANCE.NS"
    m.company_name = "Reliance"
    m.quantity = 10
    m.purchase_price = 2500.0
    m.purchase_date = date(2026, 1, 1)
    m.exchange = "NSE"
    m.broker_name = None
    m.investment_source = None
    m.notes = None
    m.created_at = dt_now
    return m


class TestExpenseServiceUserIsolation:
    def _svc(self):
        from app.services.expense_service import ExpenseService
        return ExpenseService(AsyncMock())

    @pytest.mark.asyncio
    async def test_update_expense_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        from app.schemas.expense import ExpenseUpdate
        svc = self._svc()
        svc.expense_repo.get_by_id = AsyncMock(return_value=make_mock_expense(10, USER_A_ID))
        with pytest.raises(ValidationError):
            await svc.update_expense(USER_B_ID, 10, ExpenseUpdate(amount=999.0))

    @pytest.mark.asyncio
    async def test_delete_expense_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        svc = self._svc()
        svc.expense_repo.get_by_id = AsyncMock(return_value=make_mock_expense(10, USER_A_ID))
        with pytest.raises(ValidationError):
            await svc.delete_expense(USER_B_ID, 10)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_expense_raises(self):
        from app.core.exceptions import ValidationError
        svc = self._svc()
        svc.expense_repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValidationError):
            await svc.delete_expense(USER_B_ID, 9999)

    @pytest.mark.asyncio
    async def test_owner_can_delete_own_expense(self):
        svc = self._svc()
        svc.expense_repo.get_by_id = AsyncMock(return_value=make_mock_expense(10, USER_A_ID))
        svc.expense_repo.delete = AsyncMock(return_value=True)
        assert await svc.delete_expense(USER_A_ID, 10) is True

    @pytest.mark.asyncio
    async def test_owner_can_update_own_expense(self):
        from app.schemas.expense import ExpenseUpdate, ExpenseResponse
        svc = self._svc()
        exp = make_mock_expense(10, USER_A_ID)
        svc.expense_repo.get_by_id = AsyncMock(return_value=exp)
        svc.expense_repo.update = AsyncMock(return_value=exp)
        with patch.object(ExpenseResponse, "model_validate", return_value=MagicMock(expense_id=10)):
            result = await svc.update_expense(USER_A_ID, 10, ExpenseUpdate(amount=250.0))
        assert result.expense_id == 10


class TestIncomeServiceUserIsolation:
    def _svc(self):
        from app.services.expense_service import ExpenseService
        return ExpenseService(AsyncMock())

    @pytest.mark.asyncio
    async def test_update_income_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        from app.schemas.expense import IncomeUpdate
        svc = self._svc()
        svc.income_repo.get_by_id = AsyncMock(return_value=make_mock_income(20, USER_A_ID))
        with pytest.raises(ValidationError):
            await svc.update_income(USER_B_ID, 20, IncomeUpdate(amount=9999.0))

    @pytest.mark.asyncio
    async def test_delete_income_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        svc = self._svc()
        svc.income_repo.get_by_id = AsyncMock(return_value=make_mock_income(20, USER_A_ID))
        with pytest.raises(ValidationError):
            await svc.delete_income(USER_B_ID, 20)

    @pytest.mark.asyncio
    async def test_owner_can_delete_own_income(self):
        svc = self._svc()
        svc.income_repo.get_by_id = AsyncMock(return_value=make_mock_income(20, USER_A_ID))
        svc.income_repo.delete = AsyncMock(return_value=True)
        assert await svc.delete_income(USER_A_ID, 20) is True


class TestBudgetServiceUserIsolation:
    def _svc(self):
        from app.services.expense_service import ExpenseService
        return ExpenseService(AsyncMock())

    @pytest.mark.asyncio
    async def test_delete_budget_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        svc = self._svc()
        svc.budget_repo.get_by_id = AsyncMock(return_value=make_mock_budget(30, USER_A_ID))
        with pytest.raises(ValidationError):
            await svc.delete_budget(USER_B_ID, 30)

    @pytest.mark.asyncio
    async def test_owner_can_delete_own_budget(self):
        svc = self._svc()
        svc.budget_repo.get_by_id = AsyncMock(return_value=make_mock_budget(30, USER_A_ID))
        svc.budget_repo.delete = AsyncMock(return_value=True)
        assert await svc.delete_budget(USER_A_ID, 30) is True


class TestPortfolioServiceUserIsolation:
    def _svc(self):
        from app.services.portfolio_service import PortfolioService
        s = PortfolioService.__new__(PortfolioService)
        s.session = AsyncMock()
        s.portfolio_repo = AsyncMock()
        s.stock_provider = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_update_investment_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        from app.schemas.portfolio import InvestmentUpdate
        s = self._svc()
        s.portfolio_repo.get_user_investment_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValidationError):
            await s.update_investment(USER_B_ID, 40, InvestmentUpdate(quantity=999))

    @pytest.mark.asyncio
    async def test_delete_investment_cross_user_raises(self):
        from app.core.exceptions import ValidationError
        s = self._svc()
        s.portfolio_repo.get_user_investment_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValidationError):
            await s.delete_investment(USER_B_ID, 40)

    @pytest.mark.asyncio
    async def test_owner_can_delete_own_investment(self):
        s = self._svc()
        inv = make_mock_investment(40, USER_A_ID)
        s.portfolio_repo.get_user_investment_by_id = AsyncMock(return_value=inv)
        s.portfolio_repo.delete = AsyncMock(return_value=True)
        with patch.object(s, "_audit", new=AsyncMock()):
            assert await s.delete_investment(USER_A_ID, 40) is True

    @pytest.mark.asyncio
    async def test_portfolio_summary_scoped_to_user(self):
        s = self._svc()
        s.portfolio_repo.get_user_investments = AsyncMock(return_value=[])
        summary = await s.get_portfolio_summary(USER_B_ID)
        assert summary.portfolio_value == 0.0
        s.portfolio_repo.get_user_investments.assert_called_once_with(USER_B_ID)


class TestAuthIdentityIsolation:
    def test_token_encodes_correct_user_id(self):
        from app.core.security import create_access_token, decode_token
        ta = create_access_token(USER_A_ID)
        tb = create_access_token(USER_B_ID)
        pa = decode_token(ta)
        pb = decode_token(tb)
        assert str(pa["sub"]) == str(USER_A_ID)
        assert str(pb["sub"]) == str(USER_B_ID)
        assert pa["sub"] != pb["sub"]

    def test_different_users_produce_different_tokens(self):
        from app.core.security import create_access_token
        assert create_access_token(USER_A_ID) != create_access_token(USER_B_ID)

    def test_tampered_token_raises_on_decode(self):
        from app.core.security import create_access_token, decode_token
        tok = create_access_token(USER_A_ID)
        parts = tok.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsig"
        with pytest.raises(Exception):
            decode_token(tampered)