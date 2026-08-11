"""
MarketRepository, StockHistoryRepository, NewsRepository, and SentimentRepository.
"""
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.market_model import (
    CompanyNewsModel,
    CompanySentimentModel,
    Nifty50CompanyModel,
    StockMarketHistoryModel,
)
from app.repositories.base import BaseRepository


class MarketRepository(BaseRepository[Nifty50CompanyModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Nifty50CompanyModel, session)

    async def get_all_active_constituents(self) -> List[Nifty50CompanyModel]:
        stmt = (
            select(Nifty50CompanyModel)
            .where(Nifty50CompanyModel.is_active == True)
            .order_by(Nifty50CompanyModel.company_name.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class StockHistoryRepository(BaseRepository[StockMarketHistoryModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StockMarketHistoryModel, session)

    async def get_history_by_ticker(
        self, ticker: str, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 100
    ) -> List[StockMarketHistoryModel]:
        stmt = select(StockMarketHistoryModel).where(StockMarketHistoryModel.ticker == ticker)

        if start_date:
            stmt = stmt.where(StockMarketHistoryModel.trading_date >= start_date)
        if end_date:
            stmt = stmt.where(StockMarketHistoryModel.trading_date <= end_date)

        stmt = stmt.order_by(StockMarketHistoryModel.trading_date.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class NewsRepository(BaseRepository[CompanyNewsModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CompanyNewsModel, session)

    async def get_news_by_symbol(self, symbol: str, limit: int = 10) -> List[CompanyNewsModel]:
        stmt = (
            select(CompanyNewsModel)
            .where(CompanyNewsModel.stock_symbol == symbol)
            .order_by(CompanyNewsModel.publish_date.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class SentimentRepository(BaseRepository[CompanySentimentModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CompanySentimentModel, session)

    async def get_latest_sentiment_by_ticker(self, ticker: str) -> Optional[CompanySentimentModel]:
        stmt = (
            select(CompanySentimentModel)
            .where(CompanySentimentModel.ticker == ticker)
            .order_by(CompanySentimentModel.sentiment_date.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
