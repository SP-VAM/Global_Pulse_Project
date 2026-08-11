"""
ExpenseRepository, IncomeRepository, and BudgetRepository for Expense Tracker.
"""
from typing import Any, List, Optional

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.expense_model import BudgetModel, ExpenseCategoryModel, ExpenseModel, IncomeModel
from app.repositories.base import BaseRepository


class ExpenseRepository(BaseRepository[ExpenseModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExpenseModel, session)

    async def get_user_expenses_by_month(self, user_id: int, year: int, month: int) -> List[ExpenseModel]:
        stmt = (
            select(ExpenseModel)
            .where(
                ExpenseModel.user_id == user_id,
                extract("year", ExpenseModel.expense_date) == year,
                extract("month", ExpenseModel.expense_date) == month,
            )
            .order_by(ExpenseModel.expense_date.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_monthly_spending_total(self, user_id: int, year: int, month: int) -> float:
        stmt = (
            select(func.coalesce(func.sum(ExpenseModel.amount), 0.0))
            .where(
                ExpenseModel.user_id == user_id,
                extract("year", ExpenseModel.expense_date) == year,
                extract("month", ExpenseModel.expense_date) == month,
            )
        )
        res = await self.session.execute(stmt)
        return float(res.scalar_one())


class IncomeRepository(BaseRepository[IncomeModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(IncomeModel, session)

    async def get_user_incomes_by_month(self, user_id: int, year: int, month: int) -> List[IncomeModel]:
        stmt = (
            select(IncomeModel)
            .where(
                IncomeModel.user_id == user_id,
                extract("year", IncomeModel.income_date) == year,
                extract("month", IncomeModel.income_date) == month,
            )
            .order_by(IncomeModel.income_date.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_monthly_income_total(self, user_id: int, year: int, month: int) -> float:
        stmt = (
            select(func.coalesce(func.sum(IncomeModel.amount), 0.0))
            .where(
                IncomeModel.user_id == user_id,
                extract("year", IncomeModel.income_date) == year,
                extract("month", IncomeModel.income_date) == month,
            )
        )
        res = await self.session.execute(stmt)
        return float(res.scalar_one())


class BudgetRepository(BaseRepository[BudgetModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BudgetModel, session)

    async def get_user_budgets_by_month(self, user_id: int, year: int, month: int) -> List[BudgetModel]:
        stmt = (
            select(BudgetModel)
            .where(
                BudgetModel.user_id == user_id,
                BudgetModel.budget_year == year,
                BudgetModel.budget_month == month,
            )
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
