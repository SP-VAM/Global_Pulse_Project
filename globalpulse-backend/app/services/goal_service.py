"""
GoalService (FRD-041).
Provides Financial Goal CRUD, progress tracking, and automated notification triggers:
  1. Goal milestone notifications (25%, 50%, 75%)
  2. Goal completion notifications (100%)
  3. Upcoming deadline reminders (7 days, 3 days, 1 day)
  4. Missed goal target alerts (end_date < today and not completed)
"""
from datetime import date, datetime, timezone
import logging
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.goal_model import GoalModel, GoalProgressModel, GoalStatusModel, InvestmentTypeModel
from app.db.models.notification_model import NotificationModel
from app.repositories.goal_repository import GoalProgressRepository, GoalRepository
from app.schemas.goal import GoalCreate, GoalProgressCreate, GoalProgressResponse, GoalResponse, GoalUpdate
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

DEFAULT_INVESTMENT_TYPES = [
    {"investment_name": "Gold", "description": "Physical & Digital Gold"},
    {"investment_name": "Silver", "description": "Silver assets"},
    {"investment_name": "Stocks", "description": "Equity stocks"},
    {"investment_name": "Mutual Funds", "description": "Mutual fund investments"},
    {"investment_name": "Crypto", "description": "Cryptocurrency"},
    {"investment_name": "Bonds", "description": "Government and Corporate Bonds"},
    {"investment_name": "Savings", "description": "General Cash & Savings"},
    {"investment_name": "Others", "description": "Other financial instruments"},
]

DEFAULT_STATUSES = [
    {"status_id": 1, "status_name": "In Progress", "description": "Goal is actively being saved for"},
    {"status_id": 2, "status_name": "Completed", "description": "Goal has reached 100% of target"},
    {"status_id": 3, "status_name": "Archived", "description": "Goal was archived or closed"},
]


class GoalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.goal_repo = GoalRepository(session)
        self.progress_repo = GoalProgressRepository(session)

    async def ensure_defaults(self) -> None:
        """Ensure initial investment types and goal statuses exist in database."""
        try:
            # Check investment types
            res = await self.session.execute(select(func.count()).select_from(InvestmentTypeModel))
            if res.scalar_one() == 0:
                for it in DEFAULT_INVESTMENT_TYPES:
                    self.session.add(InvestmentTypeModel(**it))
                await self.session.commit()
        except Exception as e:
            logger.debug("Investment types seeding skipped: %s", e)
            await self.session.rollback()

    async def get_or_create_investment_type(self, name: Optional[str]) -> int:
        """Get or create investment type by name, defaulting to 'Savings'."""
        clean_name = (name or "Savings").strip().title()
        stmt = select(InvestmentTypeModel).where(func.lower(InvestmentTypeModel.investment_name) == clean_name.lower())
        res = await self.session.execute(stmt)
        inv = res.scalar_one_or_none()
        if inv:
            return inv.investment_type_id

        # Insert new type
        new_inv = InvestmentTypeModel(investment_name=clean_name, description=f"{clean_name} investments")
        self.session.add(new_inv)
        await self.session.commit()
        await self.session.refresh(new_inv)
        return new_inv.investment_type_id

    async def create_goal(self, user_id: int, req: GoalCreate) -> GoalResponse:
        """Create a new goal for the authenticated user."""
        if req.target_quantity <= 0:
            raise ValidationError("Target amount must be strictly greater than 0.")
        if req.end_date and req.start_date and req.end_date < req.start_date:
            raise ValidationError("End date cannot be earlier than start date.")

        await self.ensure_defaults()
        inv_type_id = req.investment_type_id
        if not inv_type_id:
            inv_type_id = await self.get_or_create_investment_type(req.investment_name)

        goal = await self.goal_repo.create(
            {
                "user_id": user_id,
                "investment_type_id": inv_type_id,
                "goal_name": req.goal_name.strip(),
                "notes": req.notes,
                "target_quantity": req.target_quantity,
                "current_quantity": 0.0,
                "unit": req.unit or "INR",
                "end_date": req.end_date,
                "status": "ACTIVE",
            }
        )
        return await self._format_goal_response(goal)

    async def get_user_goals(self, user_id: int) -> List[GoalResponse]:
        """Retrieve all active goals for authenticated user and evaluate deadlines."""
        await self.ensure_defaults()
        goals = await self.goal_repo.get_active_goals_by_user(user_id)
        
        # Trigger lightweight deadline & missed target evaluator
        try:
            await self.evaluate_user_deadlines(user_id, goals)
        except Exception as eval_err:
            logger.debug("Goal deadline evaluation skipped: %s", eval_err)

        formatted = []
        for g in goals:
            formatted.append(await self._format_goal_response(g))
        return formatted

    async def get_goal_by_id(self, user_id: int, goal_id: int) -> GoalResponse:
        """Retrieve a specific goal ensuring strict user isolation."""
        goal = await self.goal_repo.get_by_id(goal_id)
        if not goal or goal.user_id != user_id or getattr(goal, "status", None) == "CANCELLED":
            raise ValidationError("Goal not found.")
        return await self._format_goal_response(goal)

    async def update_goal(self, user_id: int, goal_id: int, req: GoalUpdate) -> GoalResponse:
        """Update an existing goal with validation."""
        goal = await self.goal_repo.get_by_id(goal_id)
        if not goal or goal.user_id != user_id or getattr(goal, "status", None) == "CANCELLED":
            raise ValidationError("Goal not found.")

        updates = req.model_dump(exclude_unset=True)
        if "target_quantity" in updates and updates["target_quantity"] is not None:
            if updates["target_quantity"] <= 0:
                raise ValidationError("Target amount must be greater than 0.")
            # Ensure target amount cannot be decreased below current quantity
            if updates["target_quantity"] < float(goal.current_quantity):
                raise ValidationError("Target amount cannot be reduced below current accumulated progress.")

        if "end_date" in updates and updates["end_date"] is not None:
            if updates["end_date"] < date.today():
                pass

        if updates:
            goal = await self.goal_repo.update(goal_id, updates)
        return await self._format_goal_response(goal)

    async def delete_goal(self, user_id: int, goal_id: int) -> bool:
        """Soft delete a goal belonging to the authenticated user."""
        goal = await self.goal_repo.get_by_id(goal_id)
        if not goal or goal.user_id != user_id or getattr(goal, "status", None) == "CANCELLED":
            raise ValidationError("Goal not found.")
        return await self.goal_repo.soft_delete(goal_id, user_id)

    async def add_goal_progress(self, user_id: int, goal_id: int, req: GoalProgressCreate) -> GoalResponse:
        """Add contribution to goal progress and evaluate milestone & completion notifications."""
        if req.quantity_added <= 0:
            raise ValidationError("Contribution amount must be strictly greater than 0.")

        goal = await self.goal_repo.get_by_id(goal_id)
        if not goal or goal.user_id != user_id or getattr(goal, "status", None) == "CANCELLED":
            raise ValidationError("Goal not found.")

        old_quantity = float(goal.current_quantity)
        target = float(goal.target_quantity)
        new_quantity = old_quantity + float(req.quantity_added)

        old_pct = (old_quantity / target * 100) if target > 0 else 0
        new_pct = (new_quantity / target * 100) if target > 0 else 0

        prog_date = req.progress_date or date.today()
        # Record progress entry
        await self.progress_repo.create(
            {
                "goal_id": goal_id,
                "quantity_added": req.quantity_added,
                "progress_date": prog_date,
                "remarks": req.remarks or f"Added {req.asset_type or 'deposit'}",
            }
        )

        updates = {"current_quantity": new_quantity}
        # Check completion transition
        was_completed = old_pct >= 100
        is_completed = new_pct >= 100

        if not was_completed and is_completed:
            updates["status"] = "COMPLETED"

        goal = await self.goal_repo.update(goal_id, updates)

        # Trigger Milestone & Completion notifications
        try:
            await self._evaluate_progress_notifications(user_id, goal, old_pct, new_pct)
        except Exception as notif_err:
            logger.debug("Goal progress notification trigger skipped: %s", notif_err)

        return await self._format_goal_response(goal)

    async def _evaluate_progress_notifications(
        self, user_id: int, goal: GoalModel, old_pct: float, new_pct: float
    ) -> None:
        """Trigger milestone and completion notifications with deduplication."""
        notif_svc = NotificationService(self.session)

        # 1. Goal Completion (100%)
        if old_pct < 100 <= new_pct:
            title = "Goal Completed!"
            msg = f"Congratulations! You have reached your goal: {goal.goal_name}."
            if not await self._has_duplicate_notification(user_id, title, goal.goal_name):
                await notif_svc.create_and_send_notification(
                    user_id=user_id,
                    title=title,
                    message=msg,
                    notification_type="REMINDER",
                    action_url="/dashboard/goals",
                    send_push=True,
                )
            return

        # 2. Milestones: 25%, 50%, 75%
        milestones = [25, 50, 75]
        for m in milestones:
            if old_pct < m <= new_pct and new_pct < 100:
                title = "Goal Milestone Reached"
                msg = f"You've reached {m}% of your goal: {goal.goal_name}."
                if not await self._has_duplicate_notification(user_id, title, f"{m}% of your goal: {goal.goal_name}"):
                    await notif_svc.create_and_send_notification(
                        user_id=user_id,
                        title=title,
                        message=msg,
                        notification_type="REMINDER",
                        action_url="/dashboard/goals",
                        send_push=True,
                    )

    async def evaluate_user_deadlines(self, user_id: int, goals: List[GoalModel]) -> None:
        """Evaluate upcoming and missed deadlines for active goals with deduplication."""
        today = date.today()
        notif_svc = NotificationService(self.session)

        for goal in goals:
            if getattr(goal, "status", None) == "DELETED" or float(goal.current_quantity) >= float(goal.target_quantity):
                continue

            days_left = (goal.end_date - today).days

            # Upcoming deadlines: 7, 3, 1 days
            if days_left in [7, 3, 1]:
                title = "Upcoming Goal Deadline"
                msg = f"Your goal '{goal.goal_name}' is due in {days_left} day{'s' if days_left > 1 else ''} on {goal.end_date}."
                identifier = f"{goal.goal_name} (due in {days_left} days)"
                if not await self._has_duplicate_notification(user_id, title, identifier):
                    await notif_svc.create_and_send_notification(
                        user_id=user_id,
                        title=title,
                        message=msg,
                        notification_type="REMINDER",
                        action_url="/dashboard/goals",
                        send_push=True,
                    )

            # Missed deadline: end_date < today
            elif days_left < 0:
                title = "Goal Deadline Missed"
                msg = f"Your goal '{goal.goal_name}' has passed its deadline on {goal.end_date} without reaching the target."
                identifier = f"passed its deadline on {goal.end_date}: {goal.goal_name}"
                if not await self._has_duplicate_notification(user_id, title, identifier):
                    await notif_svc.create_and_send_notification(
                        user_id=user_id,
                        title=title,
                        message=msg,
                        notification_type="REMINDER",
                        action_url="/dashboard/goals",
                        send_push=True,
                    )

    async def _has_duplicate_notification(self, user_id: int, title: str, identifier: str) -> bool:
        """Check if identical notification was already persisted for this user and event."""
        stmt = (
            select(func.count())
            .select_from(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.title == title,
                NotificationModel.message.contains(identifier),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() > 0

    async def _format_goal_response(self, goal: GoalModel) -> GoalResponse:
        """Format GoalModel into GoalResponse with progress and history."""
        target = float(goal.target_quantity) if goal.target_quantity else 1.0
        current = float(goal.current_quantity) if goal.current_quantity else 0.0
        pct = round((current / target) * 100, 2)
        today = date.today()
        days_left = max(0, (goal.end_date - today).days) if goal.end_date else 0

        status_str = "Completed" if pct >= 100 else ("In Progress" if days_left > 0 else "Expired")
        status_id = 2 if pct >= 100 else 1

        history_models = await self.progress_repo.get_history_by_goal(goal.goal_id)
        history = [GoalProgressResponse.model_validate(h) for h in history_models]

        return GoalResponse(
            goal_id=goal.goal_id,
            user_id=goal.user_id,
            investment_type_id=goal.investment_type_id,
            status_id=status_id,
            goal_name=goal.goal_name,
            notes=goal.notes,
            target_quantity=float(goal.target_quantity),
            current_quantity=float(goal.current_quantity),
            unit=goal.unit,
            start_date=getattr(goal, "start_date", None) or date.today(),
            end_date=goal.end_date,
            completed_at=getattr(goal, "completed_at", None),
            is_deleted=getattr(goal, "status", None) == "DELETED",
            created_at=goal.created_at or datetime.now(timezone.utc),
            updated_at=goal.updated_at or datetime.now(timezone.utc),
            progress_pct=pct,
            days_left=days_left,
            status=status_str,
            history=history,
        )
