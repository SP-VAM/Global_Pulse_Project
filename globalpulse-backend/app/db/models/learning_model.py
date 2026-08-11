"""
SQLAlchemy ORM models for Learning Hub modules and user progress.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, BigIntegerPK


class LearningModuleModel(Base):
    __tablename__ = "learning_modules"

    module_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)  # Beginner, Intermediate, Advanced
    duration: Mapped[str] = mapped_column(String(50), nullable=False)
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserLearningProgressModel(Base):
    __tablename__ = "user_learning_progress"

    progress_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    module_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("learning_modules.module_id", ondelete="CASCADE"), nullable=False)
    last_accessed: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
