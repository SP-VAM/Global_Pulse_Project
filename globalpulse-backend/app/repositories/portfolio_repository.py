"""
Repository for User Investment Portfolio.
Strict user isolation via user_id filtering.
"""
from typing import Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.portfolio_model import UserInvestmentModel
from app.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[UserInvestmentModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserInvestmentModel, session)

    async def get_user_investments(self, user_id: int) -> List[UserInvestmentModel]:
        """Fetch all investment holdings for a user, sorted by creation date."""
        stmt = (
            select(UserInvestmentModel)
            .where(UserInvestmentModel.user_id == user_id)
            .order_by(UserInvestmentModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_user_investment_by_id(self, user_id: int, investment_id: int) -> Optional[UserInvestmentModel]:
        """Fetch a specific investment holding verified by user_id."""
        stmt = select(UserInvestmentModel).where(
            UserInvestmentModel.user_id == user_id,
            UserInvestmentModel.investment_id == investment_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
