"""
Expense Tracker Service.
Business logic for managing user expenses, incomes, budgets, and monthly totals.
"""
import logging
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.expense_model import BudgetModel, ExpenseCategoryModel, ExpenseModel, IncomeModel
from app.repositories.expense_repository import BudgetRepository, ExpenseRepository, IncomeRepository
from app.schemas.expense import (
    BudgetCreate,
    BudgetResponse,
    ExpenseCategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSummaryResponse,
    IncomeCreate,
    IncomeResponse,
)

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    {"category_name": "Rent", "icon_name": "Home", "color_code": "#3b82f6"},
    {"category_name": "Shopping", "icon_name": "ShoppingBag", "color_code": "#8b5cf6"},
    {"category_name": "Food", "icon_name": "Utensils", "color_code": "#06b6d4"},
    {"category_name": "Transport", "icon_name": "Car", "color_code": "#10b981"},
    {"category_name": "Entertainment", "icon_name": "Film", "color_code": "#f59e0b"},
    {"category_name": "Health", "icon_name": "HeartPulse", "color_code": "#ef4444"},
    {"category_name": "Bills", "icon_name": "Receipt", "color_code": "#64748b"},
]


class ExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expense_repo = ExpenseRepository(session)
        self.income_repo = IncomeRepository(session)
        self.budget_repo = BudgetRepository(session)

    async def ensure_default_categories(self) -> List[ExpenseCategoryModel]:
        """Ensure standard default expense categories exist in database."""
        stmt = select(ExpenseCategoryModel).where(ExpenseCategoryModel.is_active == True)
        res = await self.session.execute(stmt)
        existing = list(res.scalars().all())

        if not existing:
            for cat_data in DEFAULT_CATEGORIES:
                cat = ExpenseCategoryModel(**cat_data)
                self.session.add(cat)
            await self.session.commit()

            res = await self.session.execute(stmt)
            existing = list(res.scalars().all())

        return existing

    async def get_or_create_category_by_name(self, category_name: str) -> ExpenseCategoryModel:
        """Find or create category by name."""
        stmt = select(ExpenseCategoryModel).where(func.lower(ExpenseCategoryModel.category_name) == category_name.lower())
        res = await self.session.execute(stmt)
        cat = res.scalar_one_or_none()
        if not cat:
            cat = ExpenseCategoryModel(category_name=category_name.capitalize(), color_code="#64748b")
            self.session.add(cat)
            await self.session.commit()
            await self.session.refresh(cat)
        return cat

    async def get_monthly_summary(self, user_id: int, year: int, month: int) -> ExpenseSummaryResponse:
        """Fetch complete monthly financial summary for user."""
        categories = await self.ensure_default_categories()

        spending = await self.expense_repo.get_monthly_spending_total(user_id, year, month)
        income = await self.income_repo.get_monthly_income_total(user_id, year, month)
        expenses = await self.expense_repo.get_user_expenses_by_month(user_id, year, month)
        incomes = await self.income_repo.get_user_incomes_by_month(user_id, year, month)
        budgets = await self.budget_repo.get_user_budgets_by_month(user_id, year, month)

        return ExpenseSummaryResponse(
            year=year,
            month=month,
            monthly_spending=float(spending),
            monthly_income=float(income),
            savings=float(income - spending),
            expenses=[ExpenseResponse.model_validate(e) for e in expenses],
            incomes=[IncomeResponse.model_validate(i) for i in incomes],
            budgets=[BudgetResponse.model_validate(b) for b in budgets],
            categories=[ExpenseCategoryResponse.model_validate(c) for c in categories],
        )

    async def create_expense(self, user_id: int, req: ExpenseCreate) -> ExpenseResponse:
        """Record a new expense for the user."""
        cat_id = req.category_id
        if not cat_id and req.category_name:
            cat = await self.get_or_create_category_by_name(req.category_name)
            cat_id = cat.category_id
        elif not cat_id:
            categories = await self.ensure_default_categories()
            cat_id = categories[0].category_id

        expense = await self.expense_repo.create(
            {
                "user_id": user_id,
                "category_id": cat_id,
                "amount": req.amount,
                "expense_date": req.expense_date,
                "payment_method": req.payment_method,
                "notes": req.notes,
            }
        )
        return ExpenseResponse.model_validate(expense)

    async def create_income(self, user_id: int, req: IncomeCreate) -> IncomeResponse:
        """Record a new income entry for the user."""
        income = await self.income_repo.create(
            {
                "user_id": user_id,
                "amount": req.amount,
                "income_date": req.income_date,
                "payment_method": req.payment_method,
                "notes": req.notes,
            }
        )
        return IncomeResponse.model_validate(income)

    async def update_expense(self, user_id: int, expense_id: int, req: ExpenseUpdate) -> ExpenseResponse:
        """Update an existing expense belonging to user."""
        expense = await self.expense_repo.get_by_id(expense_id)
        if not expense or expense.user_id != user_id:
            raise ValidationError("Expense record not found.")

        updates = req.model_dump(exclude_unset=True)
        if "category_name" in updates:
            cat_name = updates.pop("category_name")
            if cat_name:
                cat = await self.get_or_create_category_by_name(cat_name)
                updates["category_id"] = cat.category_id

        updated = await self.expense_repo.update(expense_id, updates)
        return ExpenseResponse.model_validate(updated)

    async def delete_expense(self, user_id: int, expense_id: int) -> bool:
        """Delete an expense belonging to the user."""
        expense = await self.expense_repo.get_by_id(expense_id)
        if not expense or expense.user_id != user_id:
            raise ValidationError("Expense record not found.")
        return await self.expense_repo.delete(expense_id)

    async def update_income(self, user_id: int, income_id: int, req: IncomeUpdate) -> IncomeResponse:
        """Update an existing income belonging to user."""
        income = await self.income_repo.get_by_id(income_id)
        if not income or income.user_id != user_id:
            raise ValidationError("Income record not found.")

        updates = req.model_dump(exclude_unset=True)
        updated = await self.income_repo.update(income_id, updates)
        return IncomeResponse.model_validate(updated)

    async def delete_income(self, user_id: int, income_id: int) -> bool:
        """Delete an income entry belonging to user."""
        income = await self.income_repo.get_by_id(income_id)
        if not income or income.user_id != user_id:
            raise ValidationError("Income record not found.")
        return await self.income_repo.delete(income_id)

    async def save_budget(self, user_id: int, req: BudgetCreate) -> BudgetResponse:
        """Create or update a category budget for user."""
        cat_id = req.category_id
        if not cat_id and req.category_name:
            cat = await self.get_or_create_category_by_name(req.category_name)
            cat_id = cat.category_id
        elif not cat_id:
            categories = await self.ensure_default_categories()
            cat_id = categories[0].category_id

        stmt = select(BudgetModel).where(
            BudgetModel.user_id == user_id,
            BudgetModel.category_id == cat_id,
            BudgetModel.budget_year == req.budget_year,
            BudgetModel.budget_month == req.budget_month,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            updated = await self.budget_repo.update(existing.budget_id, {"budget_amount": req.budget_amount})
            return BudgetResponse.model_validate(updated)
        else:
            budget = await self.budget_repo.create(
                {
                    "user_id": user_id,
                    "category_id": cat_id,
                    "budget_amount": req.budget_amount,
                    "budget_month": req.budget_month,
                    "budget_year": req.budget_year,
                }
            )
            return BudgetResponse.model_validate(budget)

    async def delete_budget(self, user_id: int, budget_id: int) -> bool:
        """Delete a budget record belonging to user."""
        budget = await self.budget_repo.get_by_id(budget_id)
        if not budget or budget.user_id != user_id:
            raise ValidationError("Budget record not found.")
        return await self.budget_repo.delete(budget_id)

