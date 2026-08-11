from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Date,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.sync_database import Base


# ==========================================================
# USERS
# ==========================================================

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    mobile_number = Column(String(20), unique=True, index=True)
    password_hash = Column(Text)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=True)
    auth_provider = Column(String(20), default="LOCAL")
    is_mobile_verified = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    profile_image = Column(Text)
    account_status = Column(String(20), default="ACTIVE")
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    otp_records = relationship("OTPVerification", back_populates="user")
    social_accounts = relationship("SocialLogin", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    subscriptions = relationship("UserSubscription", back_populates="user")


# ==========================================================
# OTP VERIFICATIONS
# ==========================================================

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    otp_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
    )
    mobile_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    otp_code = Column(String(10), nullable=False)
    otp_type = Column(String(30), default="MOBILE_VERIFICATION")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="otp_records")


# ==========================================================
# GOOGLE / SOCIAL LOGINS
# ==========================================================

class SocialLogin(Base):
    __tablename__ = "social_logins"

    social_login_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String(30), nullable=False, default="GOOGLE")
    provider_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="social_accounts")


# ==========================================================
# USER SESSIONS
# ==========================================================

class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    device_name = Column(String(255))
    device_type = Column(String(50))
    ip_address = Column(String(45))
    login_time = Column(DateTime(timezone=True), server_default=func.now())
    logout_time = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")


# ==========================================================
# USER SUBSCRIPTIONS
# ==========================================================

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    subscription_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_name = Column(String(100), default="Starter")
    subscription_start = Column(DateTime(timezone=True), server_default=func.now())
    subscription_end = Column(DateTime(timezone=True))
    payment_status = Column(String(20), default="PAID")
    subscription_status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="subscriptions")


# ==========================================================
# AUDIT LOGS
# ==========================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    table_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")