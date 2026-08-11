"""
GoalRepository and GoalProgressRepository for Financial Goals management.
"""
from typing import Any, List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.goal_model import GoalModel, GoalProgressModel, InvestmentTypeModel
from app.repositories.base import BaseRepository


class GoalRepository(BaseRepository[GoalModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GoalModel, session)

    async def get_active_goals_by_user(self, user_id: int) -> List[GoalModel]:
        stmt = (
            select(GoalModel)
            .where(GoalModel.user_id == user_id, GoalModel.is_deleted == False)
            .order_by(GoalModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def soft_delete(self, goal_id: int, user_id: int) -> bool:
        stmt = (
            update(GoalModel)
            .where(GoalModel.goal_id == goal_id, GoalModel.user_id == user_id)
            .values(is_deleted=True, deleted_at=func.now())
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def get_active_count(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(GoalModel)
            .where(GoalModel.user_id == user_id, GoalModel.is_deleted == False)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()


class GoalProgressRepository(BaseRepository[GoalProgressModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GoalProgressModel, session)

    async def get_history_by_goal(self, goal_id: int) -> List[GoalProgressModel]:
        stmt = (
            select(GoalProgressModel)
            .where(GoalProgressModel.goal_id == goal_id)
            .order_by(GoalProgressModel.progress_date.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
