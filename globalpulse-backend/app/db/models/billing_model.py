"""
SQLAlchemy ORM models for Billing, Subscription Plans, and User Subscriptions.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, BigIntegerPK


class SubscriptionPlanModel(Base):
    __tablename__ = "subscription_plans"

    plan_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # Free, Pro, Elite
    price_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    features_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSubscriptionModel(Base):
    __tablename__ = "user_subscriptions"

    subscription_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscription_plans.plan_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
