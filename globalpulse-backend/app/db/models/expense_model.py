"""
SQLAlchemy ORM models for Expense Tracker (Categories, Expenses, Incomes, Budgets).
Mapped to ExpenseTracker_table.sql schema.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, BigIntegerPK


class ExpenseCategoryModel(Base):
    __tablename__ = "expense_categories"

    category_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IncomeModel(Base):
    __tablename__ = "incomes"

    income_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    income_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ExpenseModel(Base):
    __tablename__ = "expenses"

    expense_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("expense_categories.category_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    category = relationship("ExpenseCategoryModel")


class BudgetModel(Base):
    __tablename__ = "budgets"

    budget_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("expense_categories.category_id"), nullable=False)
    budget_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    budget_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    budget_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    category = relationship("ExpenseCategoryModel")
