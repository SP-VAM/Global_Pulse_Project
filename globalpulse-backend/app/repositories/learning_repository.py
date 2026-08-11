"""
LearningRepository for Learning Hub modules and user progress.
"""
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.learning_model import LearningModuleModel, UserLearningProgressModel
from app.repositories.base import BaseRepository


class LearningRepository(BaseRepository[LearningModuleModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LearningModuleModel, session)

    async def get_all_active_modules(self) -> List[LearningModuleModel]:
        stmt = (
            select(LearningModuleModel)
            .where(LearningModuleModel.is_active == True)
            .order_by(LearningModuleModel.module_id.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_user_progress(self, user_id: int) -> List[UserLearningProgressModel]:
        stmt = (
            select(UserLearningProgressModel)
            .where(UserLearningProgressModel.user_id == user_id)
            .order_by(UserLearningProgressModel.last_accessed.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
