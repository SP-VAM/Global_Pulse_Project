"""
BillingRepository for subscription plans and user subscriptions.
"""
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing_model import SubscriptionPlanModel, UserSubscriptionModel
from app.repositories.base import BaseRepository


class BillingRepository(BaseRepository[SubscriptionPlanModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SubscriptionPlanModel, session)

    async def get_active_plans(self) -> List[SubscriptionPlanModel]:
        stmt = (
            select(SubscriptionPlanModel)
            .where(SubscriptionPlanModel.is_active == True)
            .order_by(SubscriptionPlanModel.plan_id.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscriptionModel]:
        stmt = (
            select(UserSubscriptionModel)
            .where(UserSubscriptionModel.user_id == user_id, UserSubscriptionModel.status == "ACTIVE")
            .order_by(UserSubscriptionModel.started_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
