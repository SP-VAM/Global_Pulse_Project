"""
SQLAlchemy ORM models for Financial Goals, Goal Progress, and Investment Types.
Mapped directly to the PostgreSQL Railway database schema.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, BigIntegerPK


class InvestmentTypeModel(Base):
    __tablename__ = "investment_types"

    investment_type_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    investment_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)


class GoalStatusModel(Base):
    __tablename__ = "goal_statuses"

    status_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    status_name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GoalModel(Base):
    __tablename__ = "goals"

    goal_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    investment_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("investment_types.investment_type_id"), nullable=False)
    goal_name: Mapped[str] = mapped_column(String(150), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column("goal_description", Text, nullable=True)
    target_quantity: Mapped[float] = mapped_column("target_amount", Numeric(12, 2), nullable=False)
    current_quantity: Mapped[float] = mapped_column("current_amount", Numeric(12, 2), default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column("investment_unit", String(20), default="Units", nullable=False)
    end_date: Mapped[date] = mapped_column("target_date", Date, nullable=False)
    status: Mapped[str] = mapped_column("goal_status", String(30), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    progress_entries = relationship("GoalProgressModel", back_populates="goal", cascade="all, delete-orphan")


class GoalProgressModel(Base):
    __tablename__ = "goal_progress"

    progress_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    goal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("goals.goal_id", ondelete="CASCADE"), nullable=False)
    quantity_added: Mapped[float] = mapped_column("progress_amount", Numeric(12, 2), nullable=False)
    progress_date: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    goal = relationship("GoalModel", back_populates="progress_entries")
