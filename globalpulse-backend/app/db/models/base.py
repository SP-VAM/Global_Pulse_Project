"""
GlobalPulse Base Declarative Model.
"""
from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BigIntegerPK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
