"""
GlobalPulse Generic Base Repository.

Provides reusable async CRUD operations for SQLAlchemy models.
Directly implements exception translation and type safety.
"""
import logging
from typing import Any, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateRecordError, GlobalPulseError
from app.db.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic Async Repository implementing standard persistence operations.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Fetch entity by primary key."""
        return await self.session.get(self.model, id)

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """List entities with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: CreateSchemaType | dict) -> ModelType:
        """Create new entity from Pydantic schema or dictionary."""
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump(exclude_unset=True)

        db_obj = self.model(**create_data)
        self.session.add(db_obj)
        try:
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except IntegrityError as exc:
            await self.session.rollback()
            logger.error("Integrity error in create: %s", exc)
            raise DuplicateRecordError(
                f"Record violates constraint for {self.model.__name__}: {getattr(exc, 'orig', exc)}"
            ) from exc

    async def update(self, id: Any, obj_in: UpdateSchemaType | dict) -> Optional[ModelType]:
        """Update existing entity."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except IntegrityError as exc:
            await self.session.rollback()
            logger.error("Integrity error in update: %s", exc)
            raise DuplicateRecordError(
                f"Update violates unique constraint for {self.model.__name__}."
            ) from exc

    async def delete(self, id: Any) -> bool:
        """Delete entity by primary key."""
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False
        await self.session.delete(db_obj)
        await self.session.commit()
        return True

    async def count(self) -> int:
        """Return total row count."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, **kwargs) -> bool:
        """Check if any record matches filter criteria."""
        stmt = select(self.model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
