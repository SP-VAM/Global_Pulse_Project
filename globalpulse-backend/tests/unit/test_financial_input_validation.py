"""
Comprehensive Regression Test Suite for Financial Input Validation & Data Integrity.
Tests all 21 scenarios covering:
- Maximum 13 integer digits (<= 9,999,999,999,999.99)
- Maximum 2 decimal places
- Rejection of negatives, zero, NaN, Infinity, scientific notation
- String length constraints (Goal Name <= 100, Notes <= 500, etc.)
- All financial schemas: GoalCreate, GoalUpdate, GoalProgressCreate,
  ExpenseCreate, ExpenseUpdate, IncomeCreate, IncomeUpdate, BudgetCreate, BudgetUpdate,
  InvestmentCreate, InvestmentUpdate.
"""
from datetime import date
import pytest
from pydantic import ValidationError

from app.schemas.goal import GoalCreate, GoalUpdate, GoalProgressCreate
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, IncomeCreate, IncomeUpdate, BudgetCreate, BudgetUpdate
from app.schemas.portfolio import InvestmentCreate, InvestmentUpdate


class TestFinancialInputValidation:
    """Test suite covering 21 critical financial validation cases."""

    # 1. Valid 13-digit integer
    def test_tc01_valid_13_digit_integer(self):
        schema = ExpenseCreate(amount=9_999_999_999_999.0, expense_date=date.today())
        assert schema.amount == 9_999_999_999_999.0

    # 2. Valid 13-digit integer with 2 decimals
    def test_tc02_valid_13_digit_with_2_decimals(self):
        schema = ExpenseCreate(amount=9_999_999_999_999.99, expense_date=date.today())
        assert schema.amount == 9_999_999_999_999.99

    # 3. Normal financial values
    def test_tc03_normal_financial_values(self):
        schema1 = ExpenseCreate(amount=5000.0, expense_date=date.today())
        schema2 = ExpenseCreate(amount=5000.50, expense_date=date.today())
        assert schema1.amount == 5000.0
        assert schema2.amount == 5000.50

    # 4. 14-digit integer rejected
    def test_tc04_reject_14_digit_integer(self):
        with pytest.raises(ValidationError) as exc:
            ExpenseCreate(amount=10_000_000_000_000.0, expense_date=date.today())
        assert "Amount cannot exceed 13" in str(exc.value) or "less than or equal" in str(exc.value)

    # 5. 15-digit integer rejected
    def test_tc05_reject_15_digit_integer(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=100_000_000_000_000.0, expense_date=date.today())

    # 6. Negative amounts rejected
    def test_tc06_reject_negative_amount(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=-5000.0, expense_date=date.today())
        with pytest.raises(ValidationError):
            IncomeCreate(amount=-0.01, income_date=date.today())

    # 7. Zero amount rejected
    def test_tc07_reject_zero_amount(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=0.0, expense_date=date.today())
        with pytest.raises(ValidationError):
            BudgetCreate(budget_amount=0.0, budget_month=1, budget_year=2026)

    # 8. Scientific notation overflow rejected
    def test_tc08_reject_scientific_notation_overflow(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=1e20, expense_date=date.today())

    # 9. Infinity rejected
    def test_tc09_reject_infinity(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=float("inf"), expense_date=date.today())

    # 10. NaN rejected
    def test_tc10_reject_nan(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=float("nan"), expense_date=date.today())

    # 11. > 2 decimal places rejected
    def test_tc11_reject_excess_decimal_places(self):
        with pytest.raises(ValidationError) as exc:
            ExpenseCreate(amount=5000.123, expense_date=date.today())
        assert "decimal places" in str(exc.value)

    # 12. Goal creation with 14 digits rejected
    def test_tc12_goal_create_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            GoalCreate(
                goal_name="Dream House",
                target_quantity=10_000_000_000_000.0,
                end_date=date(2027, 1, 1),
            )

    # 13. Goal target update with 14 digits rejected
    def test_tc13_goal_update_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            GoalUpdate(target_quantity=10_000_000_000_000.0)

    # 14. Goal progress contribution with 14 digits rejected
    def test_tc14_goal_progress_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            GoalProgressCreate(quantity_added=10_000_000_000_000.0)

    # 15. Expense creation with 14 digits rejected
    def test_tc15_expense_create_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=10_000_000_000_000.0, expense_date=date.today())

    # 16. Expense update with 14 digits rejected
    def test_tc16_expense_update_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            ExpenseUpdate(amount=10_000_000_000_000.0)

    # 17. Income creation with 14 digits rejected
    def test_tc17_income_create_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            IncomeCreate(amount=10_000_000_000_000.0, income_date=date.today())

    # 18. Budget bucket creation with 14 digits rejected
    def test_tc18_budget_create_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            BudgetCreate(budget_amount=10_000_000_000_000.0, budget_month=5, budget_year=2026)

    # 19. Budget update with 14 digits rejected
    def test_tc19_budget_update_14_digits_rejected(self):
        with pytest.raises(ValidationError):
            BudgetUpdate(budget_amount=10_000_000_000_000.0)

    # 20. Goal name > 100 characters rejected
    def test_tc20_goal_name_length_limit(self):
        valid_name = "A" * 100
        invalid_name = "A" * 101

        # 100 chars -> Valid
        goal = GoalCreate(goal_name=valid_name, target_quantity=50000.0, end_date=date(2027, 1, 1))
        assert goal.goal_name == valid_name

        # 101 chars -> Rejected
        with pytest.raises(ValidationError):
            GoalCreate(goal_name=invalid_name, target_quantity=50000.0, end_date=date(2027, 1, 1))

    # 21. Goal notes / transaction notes > 500 characters rejected
    def test_tc21_notes_length_limit(self):
        valid_notes = "N" * 500
        invalid_notes = "N" * 501

        # 500 chars -> Valid
        exp = ExpenseCreate(amount=500.0, expense_date=date.today(), notes=valid_notes)
        assert exp.notes == valid_notes

        # 501 chars -> Rejected
        with pytest.raises(ValidationError):
            ExpenseCreate(amount=500.0, expense_date=date.today(), notes=invalid_notes)

        # Goal notes > 500 chars -> Rejected
        with pytest.raises(ValidationError):
            GoalCreate(goal_name="Valid Name", target_quantity=50000.0, end_date=date(2027, 1, 1), notes=invalid_notes)

        # Investment notes > 500 chars -> Rejected
        with pytest.raises(ValidationError):
            InvestmentCreate(
                ticker="RELIANCE.NS",
                company_name="Reliance Industries",
                quantity=10.0,
                purchase_price=2500.0,
                purchase_date=date.today(),
                notes=invalid_notes,
            )
