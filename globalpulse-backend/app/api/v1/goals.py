"""
Financial Goals API Endpoints (FRD-041).
Provides authenticated CRUD and progress tracking for user financial goals.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.core.exceptions import ValidationError
from app.db.models.user_model import UserModel
from app.db.session import get_db_session
from app.schemas.goal import GoalCreate, GoalProgressCreate, GoalResponse, GoalUpdate
from app.services.goal_service import GoalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/goals", tags=["Financial Goals (FRD-041)"])


@router.get("", response_model=List[GoalResponse])
async def list_goals(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[GoalResponse]:
    """Retrieve all active financial goals for the authenticated user."""
    service = GoalService(session)
    return await service.get_user_goals(current_user.user_id)


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    req: GoalCreate,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GoalResponse:
    """Create a new financial goal for the authenticated user."""
    service = GoalService(session)
    try:
        return await service.create_goal(current_user.user_id, req)
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to create goal: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create goal.")


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GoalResponse:
    """Get details of a specific goal belonging to the authenticated user."""
    service = GoalService(session)
    try:
        return await service.get_goal_by_id(current_user.user_id, goal_id)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: int,
    req: GoalUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GoalResponse:
    """Update goal attributes (e.g. target quantity, notes, end date)."""
    service = GoalService(session)
    try:
        return await service.update_goal(current_user.user_id, goal_id, req)
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to update goal %d: %s", goal_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update goal.")


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Soft delete a goal belonging to the authenticated user."""
    service = GoalService(session)
    try:
        deleted = await service.delete_goal(current_user.user_id, goal_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")


@router.post("/{goal_id}/progress", response_model=GoalResponse)
async def add_goal_progress(
    goal_id: int,
    req: GoalProgressCreate,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> GoalResponse:
    """Add progress deposit to a goal and trigger milestone/completion notifications."""
    service = GoalService(session)
    try:
        return await service.add_goal_progress(current_user.user_id, goal_id, req)
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to add progress to goal %d: %s", goal_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add progress.")
