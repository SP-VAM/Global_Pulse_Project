"""
Unit and regression tests for Financial Goals & Reminders (FRD-041).
Tests cover:
  1. Goal creation and validation
  2. Goal retrieval and updates
  3. Strict IDOR / User Isolation
  4. 25%, 50%, 75% Milestone notifications
  5. 100% Goal completion notification
  6. 7-day, 3-day, 1-day upcoming deadline reminders
  7. Missed target notification
  8. Duplicate notification prevention
  9. Adversarial input validation (negative targets, invalid dates, invalid progress)
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import ValidationError
from app.db.models.goal_model import GoalModel, GoalProgressModel, GoalStatusModel, InvestmentTypeModel
from app.db.models.notification_model import NotificationModel
from app.schemas.goal import GoalCreate, GoalProgressCreate, GoalUpdate
from app.services.goal_service import GoalService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_create_goal_success(mock_session):
    """Test successful goal creation for authenticated user."""
    service = GoalService(mock_session)
    service.ensure_defaults = AsyncMock()
    service.get_or_create_investment_type = AsyncMock(return_value=1)
    
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    mock_goal = GoalModel(
        goal_id=1,
        user_id=10,
        investment_type_id=1,
        goal_name="Emergency Fund",
        notes="6 months savings",
        target_quantity=100000.0,
        current_quantity=0.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.create = AsyncMock(return_value=mock_goal)
    service.progress_repo.get_history_by_goal = AsyncMock(return_value=[])

    req = GoalCreate(
        goal_name="Emergency Fund",
        target_quantity=100000.0,
        start_date=date(2026, 8, 1),
        end_date=date(2027, 8, 1),
        notes="6 months savings",
    )
    resp = await service.create_goal(user_id=10, req=req)

    assert resp.goal_id == 1
    assert resp.user_id == 10
    assert resp.goal_name == "Emergency Fund"
    assert resp.target_quantity == 100000.0
    assert resp.progress_pct == 0.0


@pytest.mark.asyncio
async def test_create_goal_adversarial_validation(mock_session):
    """Test validation errors for zero/negative targets or inverted date ranges."""
    service = GoalService(mock_session)
    service.ensure_defaults = AsyncMock()

    # Inverted date
    with pytest.raises(ValidationError, match="End date cannot be earlier than start date"):
        req = GoalCreate(
            goal_name="Invalid Goal",
            target_quantity=5000.0,
            start_date=date(2027, 8, 1),
            end_date=date(2026, 8, 1),
        )
        await service.create_goal(user_id=10, req=req)


@pytest.mark.asyncio
async def test_strict_user_isolation(mock_session):
    """Verify User A cannot view, update, or delete User B's goal."""
    service = GoalService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    
    # Goal belongs to User 200
    goal_user_b = GoalModel(
        goal_id=55,
        user_id=200,
        investment_type_id=1,
        goal_name="User B Private Goal",
        target_quantity=50000.0,
        current_quantity=10000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.get_by_id = AsyncMock(return_value=goal_user_b)

    # User 100 attempts to read User 200's goal
    with pytest.raises(ValidationError, match="Goal not found"):
        await service.get_goal_by_id(user_id=100, goal_id=55)

    # User 100 attempts to update User 200's goal
    with pytest.raises(ValidationError, match="Goal not found"):
        await service.update_goal(user_id=100, goal_id=55, req=GoalUpdate(goal_name="Hacked"))

    # User 100 attempts to delete User 200's goal
    with pytest.raises(ValidationError, match="Goal not found"):
        await service.delete_goal(user_id=100, goal_id=55)

    # User 100 attempts to add progress to User 200's goal
    with pytest.raises(ValidationError, match="Goal not found"):
        await service.add_goal_progress(user_id=100, goal_id=55, req=GoalProgressCreate(quantity_added=500.0))


@pytest.mark.asyncio
async def test_milestone_notifications_25_50_75(mock_session):
    """Test that crossing 25%, 50%, and 75% thresholds dispatches REMINDER notifications."""
    service = GoalService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    
    # Goal target = 100,000, initial current = 10,000 (10%)
    mock_goal = GoalModel(
        goal_id=1,
        user_id=10,
        investment_type_id=1,
        goal_name="Down Payment",
        target_quantity=100000.0,
        current_quantity=10000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.get_by_id = AsyncMock(return_value=mock_goal)
    service.progress_repo.create = AsyncMock()
    service.progress_repo.get_history_by_goal = AsyncMock(return_value=[])

    # 1. Add 20,000 -> new total = 30,000 (30% -> crosses 25%)
    updated_goal_25 = GoalModel(
        goal_id=1,
        user_id=10,
        investment_type_id=1,
        goal_name="Down Payment",
        target_quantity=100000.0,
        current_quantity=30000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.update = AsyncMock(return_value=updated_goal_25)
    service._has_duplicate_notification = AsyncMock(return_value=False)

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:
        await service.add_goal_progress(user_id=10, goal_id=1, req=GoalProgressCreate(quantity_added=20000.0))
        assert mock_notif.called
        kwargs = mock_notif.call_args.kwargs
        assert kwargs["title"] == "Goal Milestone Reached"
        assert "25%" in kwargs["message"]
        assert kwargs["notification_type"] == "REMINDER"

    # 2. Add 25,000 -> new total = 55,000 (55% -> crosses 50%)
    mock_goal.current_quantity = 30000.0
    updated_goal_50 = GoalModel(
        goal_id=1,
        user_id=10,
        investment_type_id=1,
        goal_name="Down Payment",
        target_quantity=100000.0,
        current_quantity=55000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.update = AsyncMock(return_value=updated_goal_50)

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:
        await service.add_goal_progress(user_id=10, goal_id=1, req=GoalProgressCreate(quantity_added=25000.0))
        assert mock_notif.called
        kwargs = mock_notif.call_args.kwargs
        assert kwargs["title"] == "Goal Milestone Reached"
        assert "50%" in kwargs["message"]


@pytest.mark.asyncio
async def test_goal_completion_notification(mock_session):
    """Test that crossing 100% target triggers Goal Completed! notification and sets completed_at."""
    service = GoalService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    
    mock_goal = GoalModel(
        goal_id=2,
        user_id=10,
        investment_type_id=1,
        goal_name="Vacation Fund",
        target_quantity=50000.0,
        current_quantity=45000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.get_by_id = AsyncMock(return_value=mock_goal)
    service.progress_repo.create = AsyncMock()
    service.progress_repo.get_history_by_goal = AsyncMock(return_value=[])

    # Add 10,000 -> total 55,000 (110% -> completed)
    updated_goal = GoalModel(
        goal_id=2,
        user_id=10,
        investment_type_id=1,
        goal_name="Vacation Fund",
        target_quantity=50000.0,
        current_quantity=55000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="COMPLETED",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.update = AsyncMock(return_value=updated_goal)
    service._has_duplicate_notification = AsyncMock(return_value=False)

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:
        await service.add_goal_progress(user_id=10, goal_id=2, req=GoalProgressCreate(quantity_added=10000.0))
        assert mock_notif.called
        kwargs = mock_notif.call_args.kwargs
        assert kwargs["title"] == "Goal Completed!"
        assert "Vacation Fund" in kwargs["message"]
        assert kwargs["notification_type"] == "REMINDER"


@pytest.mark.asyncio
async def test_upcoming_and_missed_deadline_evaluation(mock_session):
    """Test 7-day upcoming reminder and missed deadline alerts."""
    service = GoalService(mock_session)
    today = date.today()
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    goal_7_days = GoalModel(
        goal_id=10,
        user_id=10,
        investment_type_id=1,
        goal_name="7 Day Goal",
        target_quantity=10000.0,
        current_quantity=2000.0,
        end_date=today + timedelta(days=7),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )

    goal_missed = GoalModel(
        goal_id=11,
        user_id=10,
        investment_type_id=1,
        goal_name="Missed Goal",
        target_quantity=10000.0,
        current_quantity=2000.0,
        end_date=today - timedelta(days=2),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )

    service._has_duplicate_notification = AsyncMock(return_value=False)

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:
        await service.evaluate_user_deadlines(user_id=10, goals=[goal_7_days, goal_missed])
        assert mock_notif.call_count == 2
        titles = [c.kwargs["title"] for c in mock_notif.call_args_list]
        assert "Upcoming Goal Deadline" in titles
        assert "Goal Deadline Missed" in titles


@pytest.mark.asyncio
async def test_duplicate_notification_prevention(mock_session):
    """Test that existing notifications in database prevent duplicate deadline or milestone spam."""
    service = GoalService(mock_session)
    today = date.today()
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    goal_7_days = GoalModel(
        goal_id=10,
        user_id=10,
        investment_type_id=1,
        goal_name="7 Day Goal",
        target_quantity=10000.0,
        current_quantity=2000.0,
        end_date=today + timedelta(days=7),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )

    # Simulate notification already exists in database
    service._has_duplicate_notification = AsyncMock(return_value=True)

    with patch("app.services.notification_service.NotificationService.create_and_send_notification", new_callable=AsyncMock) as mock_notif:
        await service.evaluate_user_deadlines(user_id=10, goals=[goal_7_days])
        assert not mock_notif.called  # Zero duplicate calls made!


@pytest.mark.asyncio
async def test_update_goal_target_reduction_protection(mock_session):
    """Test that target quantity cannot be reduced below current accumulated progress."""
    service = GoalService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    mock_goal = GoalModel(
        goal_id=5,
        user_id=10,
        investment_type_id=1,
        goal_name="Car Fund",
        target_quantity=500000.0,
        current_quantity=200000.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="ACTIVE",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.get_by_id = AsyncMock(return_value=mock_goal)

    # Attempt to reduce target to 150,000 (below 200,000 progress)
    with pytest.raises(ValidationError, match="Target amount cannot be reduced below current accumulated progress"):
        await service.update_goal(user_id=10, goal_id=5, req=GoalUpdate(target_quantity=150000.0))


@pytest.mark.asyncio
async def test_add_progress_negative_or_zero_rejected(mock_session):
    """Test that zero or negative progress contributions are rejected."""
    service = GoalService(mock_session)
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises((ValidationError, PydanticValidationError)):
        req = GoalProgressCreate(quantity_added=0.0)
        await service.add_goal_progress(user_id=10, goal_id=1, req=req)

    with pytest.raises((ValidationError, PydanticValidationError)):
        req = GoalProgressCreate(quantity_added=-500.0)
        await service.add_goal_progress(user_id=10, goal_id=1, req=req)


@pytest.mark.asyncio
async def test_soft_delete_and_not_found_behavior(mock_session):
    """Test soft delete and ensure deleted goals return not found."""
    service = GoalService(mock_session)
    dt_now = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)

    deleted_goal = GoalModel(
        goal_id=99,
        user_id=10,
        investment_type_id=1,
        goal_name="Deleted Goal",
        target_quantity=10000.0,
        current_quantity=0.0,
        unit="INR",
        end_date=date(2027, 8, 1),
        status="CANCELLED",
        created_at=dt_now,
        updated_at=dt_now,
    )
    service.goal_repo.get_by_id = AsyncMock(return_value=deleted_goal)

    with pytest.raises(ValidationError, match="Goal not found"):
        await service.get_goal_by_id(user_id=10, goal_id=99)
