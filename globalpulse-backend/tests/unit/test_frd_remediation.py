"""
Focused Automated Tests for FRD Remediation & Bug Fixes:
- Bug 1: Income Payment Methods (CASH, CARD, UPI, NET_BANKING, WALLET, SALARY, OTHER)
- Bug 2: FRD-017 Budget Alerts (0%, below 80%, 80% approaching, 100%, >100% exceeded, month/user isolation, recalculation)
- Bug 3: FRD-017 Budget Unique / Upsert Handling (category, month, year, user isolation)
- Bug 4: FRD-022 Search & Filters (keyword, category, date range, amount range, transaction type, multi-filter, user isolation)
- Bug 5: Delete Authorization Ownership Protection (User A vs User B)
"""
from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ValidationError
from app.db.models import Base
from app.repositories.user_repository import UserRepository
from app.schemas.expense import (
    BudgetCreate,
    ExpenseCreate,
    ExpenseUpdate,
    IncomeCreate,
    IncomeUpdate,
    TransactionFilterParams,
)
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


async def _create_test_user(db_session: AsyncSession, username: str, email: str) -> int:
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        {
            "username": username,
            "email": email,
            "mobile_number": f"+919{hash(username) % 100000000:08d}",
            "password_hash": "hashed_pw",
            "auth_provider": "LOCAL",
            "is_mobile_verified": True,
            "account_status": "ACTIVE",
        }
    )
    return user.user_id


# ===========================================================================
# BUG 1: PAYMENT METHOD NORMALIZATION & ACCEPTANCE
# ===========================================================================

@pytest.mark.asyncio
async def test_income_payment_methods_supported():
    async with TestSessionLocal() as db:
        user_id = await _create_test_user(db, "pm_user", "pm@test.com")
        service = ExpenseService(db)

        methods = ["Cash", "Card", "UPI", "Net Banking", "Wallet", "Salary", "Other"]
        for m in methods:
            inc = await service.create_income(
                user_id,
                IncomeCreate(amount=1000.0, income_date=date(2026, 8, 1), payment_method=m, notes=f"Test {m}"),
            )
            assert inc.income_id is not None
            # Normalized value stored
            expected_norm = m.strip().upper().replace(" ", "_")
            assert inc.payment_method == expected_norm


# ===========================================================================
# BUG 2: FRD-017 BUDGET ALERTS (APPROACHING & EXCEEDED)
# ===========================================================================

@pytest.mark.asyncio
async def test_budget_alerts_lifecycle_and_isolation():
    async with TestSessionLocal() as db:
        user_a = await _create_test_user(db, "user_a", "usera@test.com")
        user_b = await _create_test_user(db, "user_b", "userb@test.com")
        service = ExpenseService(db)

        # Budget of 10,000 for Food in August 2026 for user_a
        budget = await service.save_budget(
            user_a,
            BudgetCreate(category_name="Food", budget_amount=10000.0, budget_month=8, budget_year=2026),
        )
        cat_id = budget.category_id

        # Case A: 0% spending -> no alert
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 0

        # Case B: Below 80% (e.g. 5,000 / 50%) -> no alert
        exp1 = await service.create_expense(
            user_a,
            ExpenseCreate(category_id=cat_id, amount=5000.0, expense_date=date(2026, 8, 5), notes="Groceries 1"),
        )
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 0

        # Case C: Exactly at 80% threshold (additional 3,000 -> total 8,000 / 80%) -> approaching alert
        exp2 = await service.create_expense(
            user_a,
            ExpenseCreate(category_id=cat_id, amount=3000.0, expense_date=date(2026, 8, 10), notes="Groceries 2"),
        )
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 1
        assert summary.budget_alerts[0].alert_type == "approaching"
        assert summary.budget_alerts[0].spent == 8000.0
        assert summary.budget_alerts[0].utilization_pct == 80.0

        # Case D: Between 80% and 100% (additional 1,000 -> total 9,000 / 90%) -> approaching alert
        exp3 = await service.create_expense(
            user_a,
            ExpenseCreate(category_id=cat_id, amount=1000.0, expense_date=date(2026, 8, 15), notes="Dinner"),
        )
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 1
        assert summary.budget_alerts[0].alert_type == "approaching"
        assert summary.budget_alerts[0].spent == 9000.0
        assert summary.budget_alerts[0].utilization_pct == 90.0

        # Case E: Exactly at 100% (additional 1,000 -> total 10,000 / 100%) -> approaching alert
        exp4 = await service.create_expense(
            user_a,
            ExpenseCreate(category_id=cat_id, amount=1000.0, expense_date=date(2026, 8, 20), notes="Snacks"),
        )
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 1
        assert summary.budget_alerts[0].alert_type == "approaching"
        assert summary.budget_alerts[0].spent == 10000.0
        assert summary.budget_alerts[0].utilization_pct == 100.0

        # Case F: Above 100% (additional 500 -> total 10,500 / 105%) -> exceeded alert
        exp5 = await service.create_expense(
            user_a,
            ExpenseCreate(category_id=cat_id, amount=500.0, expense_date=date(2026, 8, 22), notes="Extra snack"),
        )
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 1
        assert summary.budget_alerts[0].alert_type == "exceeded"
        assert summary.budget_alerts[0].spent == 10500.0
        assert summary.budget_alerts[0].utilization_pct == 105.0

        # Case G: Previous-month expense (July 2026) -> must not affect August budget
        await service.create_expense(
            user_a,
            ExpenseCreate(category_id=cat_id, amount=20000.0, expense_date=date(2026, 7, 10), notes="July expense"),
        )
        # August summary still reflects August expenses only
        summary_aug = await service.get_monthly_summary(user_a, 2026, 8)
        assert summary_aug.budget_alerts[0].spent == 10500.0

        # Case H: Different category expense (e.g. Rent) -> must not affect Food budget
        rent_cat = await service.get_or_create_category_by_name("Rent")
        await service.create_expense(
            user_a,
            ExpenseCreate(category_id=rent_cat.category_id, amount=50000.0, expense_date=date(2026, 8, 1), notes="Rent"),
        )
        summary_aug = await service.get_monthly_summary(user_a, 2026, 8)
        food_alerts = [a for a in summary_aug.budget_alerts if a.category_id == cat_id]
        assert len(food_alerts) == 1
        assert food_alerts[0].spent == 10500.0

        # Case I: Different user spending -> User B's spending cannot trigger or affect User A's alerts
        await service.create_expense(
            user_b,
            ExpenseCreate(category_id=cat_id, amount=50000.0, expense_date=date(2026, 8, 5), notes="User B Food"),
        )
        summary_user_b = await service.get_monthly_summary(user_b, 2026, 8)
        # User B has no budget, so 0 alerts
        assert len(summary_user_b.budget_alerts) == 0

        # Case J: Delete expense causing spending to fall below threshold -> status recalculates
        await service.delete_expense(user_a, exp5.expense_id)
        await service.delete_expense(user_a, exp4.expense_id)
        await service.delete_expense(user_a, exp3.expense_id)
        # Total is now 8,000 -> back to approaching (80%)
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 1
        assert summary.budget_alerts[0].alert_type == "approaching"

        # Delete exp2 (3,000) -> total becomes 5,000 (50%) -> no alert
        await service.delete_expense(user_a, exp2.expense_id)
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 0

        # Case K: Update expense causing spending to cross threshold -> status updates
        await service.update_expense(user_a, exp1.expense_id, ExpenseUpdate(amount=12000.0))
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budget_alerts) == 1
        assert summary.budget_alerts[0].alert_type == "exceeded"
        assert summary.budget_alerts[0].spent == 12000.0


# ===========================================================================
# BUG 3: FRD-017 BUDGET UNIQUE & UPSERT BEHAVIOR
# ===========================================================================

@pytest.mark.asyncio
async def test_budget_unique_and_upsert():
    async with TestSessionLocal() as db:
        user_a = await _create_test_user(db, "bud_user_a", "buda@test.com")
        user_b = await _create_test_user(db, "bud_user_b", "budb@test.com")
        service = ExpenseService(db)

        # 1. Create first budget
        b1 = await service.save_budget(
            user_a,
            BudgetCreate(category_name="Shopping", budget_amount=5000.0, budget_month=8, budget_year=2026),
        )
        assert b1.budget_amount == 5000.0

        # 2. Same user, category, month, year -> updates the existing budget (upsert)
        b2 = await service.save_budget(
            user_a,
            BudgetCreate(category_name="Shopping", budget_amount=7500.0, budget_month=8, budget_year=2026),
        )
        assert b2.budget_id == b1.budget_id
        assert b2.budget_amount == 7500.0

        # Verify only 1 budget row in summary
        summary = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary.budgets) == 1

        # 3. Different category -> succeeds
        b3 = await service.save_budget(
            user_a,
            BudgetCreate(category_name="Transport", budget_amount=3000.0, budget_month=8, budget_year=2026),
        )
        assert b3.budget_id != b1.budget_id

        # 4. Different month -> succeeds
        b4 = await service.save_budget(
            user_a,
            BudgetCreate(category_name="Shopping", budget_amount=6000.0, budget_month=9, budget_year=2026),
        )
        assert b4.budget_id != b1.budget_id

        # 5. Different year -> succeeds
        b5 = await service.save_budget(
            user_a,
            BudgetCreate(category_name="Shopping", budget_amount=6000.0, budget_month=8, budget_year=2027),
        )
        assert b5.budget_id != b1.budget_id

        # 6. Different user -> succeeds
        b6 = await service.save_budget(
            user_b,
            BudgetCreate(category_name="Shopping", budget_amount=5000.0, budget_month=8, budget_year=2026),
        )
        assert b6.user_id == user_b
        assert b6.budget_id != b1.budget_id


# ===========================================================================
# BUG 4: FRD-022 SEARCH & FILTERS
# ===========================================================================

@pytest.mark.asyncio
async def test_search_and_filters():
    async with TestSessionLocal() as db:
        user_a = await _create_test_user(db, "filter_user_a", "filtera@test.com")
        user_b = await _create_test_user(db, "filter_user_b", "filterb@test.com")
        service = ExpenseService(db)

        # Create transactions for user_a
        food = await service.get_or_create_category_by_name("Food")
        travel = await service.get_or_create_category_by_name("Transport")

        # Exp 1: Food, 500, 2026-08-01, UPI, "Italian Restaurant dinner"
        await service.create_expense(
            user_a,
            ExpenseCreate(category_id=food.category_id, amount=500.0, expense_date=date(2026, 8, 1), payment_method="UPI", notes="Italian Restaurant dinner"),
        )
        # Exp 2: Food, 1200, 2026-08-10, Card, "Grocery supermarket"
        await service.create_expense(
            user_a,
            ExpenseCreate(category_id=food.category_id, amount=1200.0, expense_date=date(2026, 8, 10), payment_method="Card", notes="Grocery supermarket"),
        )
        # Exp 3: Transport, 350, 2026-08-15, UPI, "Metro train card recharge"
        await service.create_expense(
            user_a,
            ExpenseCreate(category_id=travel.category_id, amount=350.0, expense_date=date(2026, 8, 15), payment_method="UPI", notes="Metro train card recharge"),
        )
        # Inc 1: Salary, 50000, 2026-08-01, Salary, "Monthly stipend"
        await service.create_income(
            user_a,
            IncomeCreate(amount=50000.0, income_date=date(2026, 8, 1), payment_method="Salary", notes="Monthly stipend"),
        )

        # Transaction for user_b (Isolation check)
        await service.create_expense(
            user_b,
            ExpenseCreate(category_id=food.category_id, amount=9999.0, expense_date=date(2026, 8, 1), payment_method="UPI", notes="Italian Restaurant dinner"),
        )

        # Filter 1: No filters -> returns all user_a transactions (3 expenses + 1 income = 4)
        res = await service.get_filtered_transactions(user_a, TransactionFilterParams())
        assert res.total == 4

        # Filter 2: Keyword "restaurant" -> matches Exp 1 only
        res = await service.get_filtered_transactions(user_a, TransactionFilterParams(keyword="restaurant"))
        assert res.total == 1
        assert res.items[0].amount == 500.0

        # Filter 3: Category = Food -> Exp 1 and Exp 2 (2 items)
        res = await service.get_filtered_transactions(user_a, TransactionFilterParams(category_id=food.category_id))
        assert res.total == 2

        # Filter 4: Date range 2026-08-05 to 2026-08-12 -> Exp 2 only
        res = await service.get_filtered_transactions(
            user_a, TransactionFilterParams(date_from=date(2026, 8, 5), date_to=date(2026, 8, 12))
        )
        assert res.total == 1
        assert res.items[0].notes == "Grocery supermarket"

        # Filter 5: Amount min=400, max=1000 -> Exp 1 (500.0) only
        res = await service.get_filtered_transactions(
            user_a, TransactionFilterParams(amount_min=400.0, amount_max=1000.0)
        )
        assert res.total == 1
        assert res.items[0].amount == 500.0

        # Filter 6: Transaction type = income -> Inc 1 (50000) only
        res = await service.get_filtered_transactions(user_a, TransactionFilterParams(transaction_type="income"))
        assert res.total == 1
        assert res.items[0].transaction_type == "income"
        assert res.items[0].amount == 50000.0

        # Filter 7: Combined multi-filter: category=Food, amount_min=1000, keyword="supermarket" -> Exp 2
        res = await service.get_filtered_transactions(
            user_a,
            TransactionFilterParams(
                category_id=food.category_id,
                amount_min=1000.0,
                keyword="supermarket",
                transaction_type="expense",
            ),
        )
        assert res.total == 1
        assert res.items[0].notes == "Grocery supermarket"

        # Filter 8: Empty result
        res = await service.get_filtered_transactions(user_a, TransactionFilterParams(keyword="nonexistent_xyz"))
        assert res.total == 0
        assert res.items == []

        # Filter 9: User isolation — User A keyword "Italian" MUST NOT return User B's 9999.0 expense
        res = await service.get_filtered_transactions(user_a, TransactionFilterParams(keyword="Italian"))
        assert res.total == 1
        assert res.items[0].amount == 500.0  # Only user_a's 500.0 expense, never user_b's 9999.0


# ===========================================================================
# BUG 5: DELETE AUTHORIZATION SECURITY REGRESSION TEST
# ===========================================================================

@pytest.mark.asyncio
async def test_delete_cross_user_authorization_rejected():
    async with TestSessionLocal() as db:
        user_a = await _create_test_user(db, "auth_user_a", "autha@test.com")
        user_b = await _create_test_user(db, "auth_user_b", "authb@test.com")
        service = ExpenseService(db)

        # User A creates expense & income
        exp_a = await service.create_expense(
            user_a,
            ExpenseCreate(category_name="Shopping", amount=2500.0, expense_date=date(2026, 8, 1), notes="User A shoes"),
        )
        inc_a = await service.create_income(
            user_a,
            IncomeCreate(amount=30000.0, income_date=date(2026, 8, 1), notes="User A freelance"),
        )

        # 1. User B attempts to delete User A's expense -> MUST raise ValidationError
        with pytest.raises(ValidationError, match="Expense record not found"):
            await service.delete_expense(user_b, exp_a.expense_id)

        # 2. User B attempts to delete User A's income -> MUST raise ValidationError
        with pytest.raises(ValidationError, match="Income record not found"):
            await service.delete_income(user_b, inc_a.income_id)

        # 3. Verify records STILL EXIST in database for User A
        summary_a = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary_a.expenses) == 1
        assert summary_a.expenses[0].expense_id == exp_a.expense_id
        assert len(summary_a.incomes) == 1
        assert summary_a.incomes[0].income_id == inc_a.income_id

        # 4. User A deletes their OWN records -> MUST succeed
        del_exp = await service.delete_expense(user_a, exp_a.expense_id)
        assert del_exp is True
        del_inc = await service.delete_income(user_a, inc_a.income_id)
        assert del_inc is True

        # 5. Verify records are now gone
        summary_a_after = await service.get_monthly_summary(user_a, 2026, 8)
        assert len(summary_a_after.expenses) == 0
        assert len(summary_a_after.incomes) == 0
