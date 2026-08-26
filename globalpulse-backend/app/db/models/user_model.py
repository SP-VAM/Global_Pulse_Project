"""
SQLAlchemy ORM models for User Identity, Auth, Sessions, Audit, and Settings.
Mapped to User_table.sql schema.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, BigIntegerPK


class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    mobile_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="LOCAL", nullable=False)
    is_mobile_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    account_status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    otps = relationship("OtpVerificationModel", back_populates="user", cascade="all, delete-orphan")
    social_logins = relationship("SocialLoginModel", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="user")
    settings = relationship("UserSettingsModel", back_populates="user", uselist=False, cascade="all, delete-orphan")


class OtpVerificationModel(Base):
    __tablename__ = "otp_verifications"

    otp_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mobile_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    target: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel: Mapped[str] = mapped_column(String(10), default="EMAIL", nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), default="PROFILE_CHANGE", nullable=False)
    otp_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    otp_code_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    otp_type: Mapped[str] = mapped_column(String(30), default="MOBILE_VERIFICATION", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserModel", back_populates="otps")


class SocialLoginModel(Base):
    __tablename__ = "social_logins"

    social_login_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserModel", back_populates="social_logins")


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    login_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    logout_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserModel", back_populates="sessions")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    module_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserModel", back_populates="audit_logs")


class UserSettingsModel(Base):
    __tablename__ = "user_settings"

    setting_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    price_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    two_factor_auth: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    budget_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    monthly_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stock_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ml_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    news_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    learning_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("UserModel", back_populates="settings")


class CustomerReviewModel(Base):
    __tablename__ = "customer_reviews"

    review_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    review_title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="PUBLISHED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("UserModel")

