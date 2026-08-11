"""
SQLAlchemy ORM models for Market Analysis, Stocks, Technical Indicators, News, and Sentiments.
Mapped to MarketAnalysis_*.sql schemas.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, LargeBinary, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, BigIntegerPK


class Nifty50CompanyModel(Base):
    __tablename__ = "nifty50_companies"

    company_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    company_symbol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StockMarketHistoryModel(Base):
    __tablename__ = "stock_market_history"

    stock_history_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    high_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    low_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    close_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    adjusted_close_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    quarter: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    month: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    sma20: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    sma50: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    ema20: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    ema50: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    rsi: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    macd: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    macd_signal: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    macd_hist: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    price_change: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    price_change_percentage: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    sentiment_mean: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CompanyNewsModel(Base):
    __tablename__ = "company_news"

    news_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    stock_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    publish_date: Mapped[date] = mapped_column(Date, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CompanySentimentModel(Base):
    __tablename__ = "company_sentiments"

    sentiment_id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    sentiment_date: Mapped[date] = mapped_column(Date, nullable=False)
    sentiment_mean: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    sentiment_count: Mapped[int] = mapped_column(default=0)
    sentiment_positive: Mapped[int] = mapped_column(default=0)
    sentiment_neutral: Mapped[int] = mapped_column(default=0)
    sentiment_negative: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
