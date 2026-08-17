"""
ExpenseRepository, IncomeRepository, and BudgetRepository for Expense Tracker.
"""
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import extract, func, or_, select
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

    async def filter_expenses(
        self,
        user_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
    ) -> List[ExpenseModel]:
        """
        Filter expenses with multiple optional criteria.
        CRITICAL: user_id is always enforced — User A cannot retrieve User B's data.
        All criteria are applied at the database level (no client-side filtering).
        """
        stmt = select(ExpenseModel).where(ExpenseModel.user_id == user_id)

        if year is not None:
            stmt = stmt.where(extract("year", ExpenseModel.expense_date) == year)
        if month is not None:
            stmt = stmt.where(extract("month", ExpenseModel.expense_date) == month)
        if category_id is not None:
            stmt = stmt.where(ExpenseModel.category_id == category_id)
        if date_from is not None:
            stmt = stmt.where(ExpenseModel.expense_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(ExpenseModel.expense_date <= date_to)
        if amount_min is not None:
            stmt = stmt.where(ExpenseModel.amount >= amount_min)
        if amount_max is not None:
            stmt = stmt.where(ExpenseModel.amount <= amount_max)
        if keyword:
            kw = f"%{keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    ExpenseModel.notes.ilike(kw),
                    ExpenseModel.payment_method.ilike(kw),
                )
            )

        stmt = stmt.order_by(ExpenseModel.expense_date.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


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

    async def filter_incomes(
        self,
        user_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
        keyword: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
    ) -> List[IncomeModel]:
        """
        Filter incomes with multiple optional criteria.
        CRITICAL: user_id is always enforced — User A cannot retrieve User B's data.
        """
        stmt = select(IncomeModel).where(IncomeModel.user_id == user_id)

        if year is not None:
            stmt = stmt.where(extract("year", IncomeModel.income_date) == year)
        if month is not None:
            stmt = stmt.where(extract("month", IncomeModel.income_date) == month)
        if date_from is not None:
            stmt = stmt.where(IncomeModel.income_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(IncomeModel.income_date <= date_to)
        if amount_min is not None:
            stmt = stmt.where(IncomeModel.amount >= amount_min)
        if amount_max is not None:
            stmt = stmt.where(IncomeModel.amount <= amount_max)
        if keyword:
            kw = f"%{keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    IncomeModel.notes.ilike(kw),
                    IncomeModel.payment_method.ilike(kw),
                )
            )

        stmt = stmt.order_by(IncomeModel.income_date.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


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
