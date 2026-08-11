"""
SQLAlchemy Model for Investment Portfolio.
Table: user_investments
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, Date, DateTime, Numeric, String, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.models.base import Base


class UserInvestmentModel(Base):
    __tablename__ = "user_investments"

    investment_id: int = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id: int = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type: str = Column(String(30), nullable=False, default="STOCKS")
    ticker: str = Column(String(30), nullable=False, index=True)
    company_name: str = Column(String(150), nullable=False)
    quantity: float = Column(Numeric(14, 4), nullable=False)
    purchase_price: float = Column(Numeric(14, 2), nullable=False)
    purchase_date: date = Column(Date, nullable=False)
    exchange: Optional[str] = Column(String(20), default="NSE")
    broker_name: Optional[str] = Column(String(50), nullable=True)
    investment_source: str = Column(String(30), default="MANUAL")
    notes: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserModel", backref="investments")
