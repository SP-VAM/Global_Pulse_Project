"""
SQLAlchemy ORM models for Financial Goals, Goal Progress, and Audit logs.
Mapped to Goals_Table.sql schema.
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
    default_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    status_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("goal_statuses.status_id"), default=1, nullable=False)
    goal_name: Mapped[str] = mapped_column(String(150), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    progress_entries = relationship("GoalProgressModel", back_populates="goal", cascade="all, delete-orphan")


class GoalProgressModel(Base):
    __tablename__ = "goal_progress"

    progress_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    goal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("goals.goal_id", ondelete="CASCADE"), nullable=False)
    quantity_added: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    progress_date: Mapped[date] = mapped_column(Date, default=func.current_date(), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    goal = relationship("GoalModel", back_populates="progress_entries")
