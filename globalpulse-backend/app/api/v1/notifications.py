"""
FastAPI Notification Endpoints for FRD-048 Push Notifications.
Prefix: /notifications
Protected by JWT authentication dependency (get_current_active_user).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.models.user_model import UserModel
from app.db.session import get_db_session
from app.schemas.notification import (
    DeviceTokenDeregisterRequest,
    DeviceTokenRegisterRequest,
    MarkReadResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
    SendNotificationRequest,
    UnreadCountResponse,
    WatchlistAddRequest,
    WatchlistItemSchema,
    WatchlistListResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Push Notifications"])


@router.get("", response_model=NotificationListResponse, status_code=status.HTTP_200_OK)
async def get_notifications(
    limit: int = Query(50, ge=1, le=100, description="Max notifications to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Fetch notifications for the authenticated user, newest first.
    Strictly isolated to current_user.user_id.
    """
    service = NotificationService(db)
    items, unread_count, total_count = await service.get_user_notifications(
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(item) for item in items],
        unread_count=unread_count,
        total_count=total_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse, status_code=status.HTTP_200_OK)
async def get_unread_notification_count(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get the authoritative unread notification count for the authenticated user.
    """
    service = NotificationService(db)
    count = await service.get_unread_count(user_id=current_user.user_id)
    return UnreadCountResponse(unread_count=count)


@router.patch("/read-all", response_model=MarkReadResponse, status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Mark all unread notifications as read for the authenticated user.
    """
    service = NotificationService(db)
    updated_count = await service.mark_all_as_read(user_id=current_user.user_id)
    return MarkReadResponse(
        success=True,
        updated_count=updated_count,
        message=f"{updated_count} notifications marked as read.",
    )


@router.delete("/clear-read", status_code=status.HTTP_200_OK)
async def clear_read_notifications(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete all read notifications belonging to the authenticated user.
    Strictly isolated to current_user.user_id. Unread notifications remain untouched.
    """
    service = NotificationService(db)
    deleted_count = await service.delete_read_notifications(user_id=current_user.user_id)
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"{deleted_count} read notifications cleared successfully.",
    }


@router.patch("/{notification_id}/read", response_model=MarkReadResponse, status_code=status.HTTP_200_OK)
async def mark_single_notification_read(
    notification_id: int = Path(..., description="ID of the notification to mark read"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Mark a single notification as read.
    Enforces user ownership: raises 404 if notification not owned by current user.
    """
    service = NotificationService(db)
    notification = await service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.user_id,
    )
    return MarkReadResponse(
        success=True,
        notification_id=notification.notification_id,
        updated_count=1,
        message="Notification marked as read.",
    )


@router.post("/device-token", status_code=status.HTTP_200_OK)
async def register_device_token(
    payload: DeviceTokenRegisterRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register or update active FCM push notification device token for authenticated user.
    """
    service = NotificationService(db)
    await service.register_device_token(
        user_id=current_user.user_id,
        fcm_token=payload.fcm_token,
        device_type=payload.device_type,
    )
    return {"success": True, "message": "Device push token registered successfully."}


@router.delete("/device-token", status_code=status.HTTP_200_OK)
async def deregister_device_token(
    payload: DeviceTokenDeregisterRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Deregister an FCM push token on user logout.
    """
    service = NotificationService(db)
    removed = await service.deregister_device_token(
        user_id=current_user.user_id,
        fcm_token=payload.fcm_token,
    )
    return {"success": removed, "message": "Device token deregistered."}


@router.post("/send", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def trigger_notification(
    payload: SendNotificationRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Dispatch a notification to a user.
    Regular users can only dispatch to themselves; cross-user dispatch requires ADMIN role.
    """
    target_user_id = current_user.user_id
    if payload.user_id and payload.user_id != current_user.user_id:
        if getattr(current_user, "role", "USER") != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can send notifications to other users.",
            )
        target_user_id = payload.user_id

    service = NotificationService(db)
    notification = await service.create_and_send_notification(
        user_id=target_user_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        action_url=payload.action_url,
        send_push=payload.send_push,
    )
    return NotificationResponse.model_validate(notification)


@router.get("/preferences", response_model=NotificationPreferencesResponse, status_code=status.HTTP_200_OK)
async def get_notification_preferences(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get notification category preferences and timezone for current authenticated user."""
    from app.services.proactive_notification_service import ProactiveNotificationService
    svc = ProactiveNotificationService(db)
    settings = await svc.get_user_settings(current_user.user_id)
    return NotificationPreferencesResponse.model_validate(settings)


@router.put("/preferences", response_model=NotificationPreferencesResponse, status_code=status.HTTP_200_OK)
async def update_notification_preferences(
    payload: NotificationPreferencesUpdateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update notification category preferences for current authenticated user."""
    from app.services.proactive_notification_service import ProactiveNotificationService
    svc = ProactiveNotificationService(db)
    settings = await svc.get_user_settings(current_user.user_id)

    for field, val in payload.model_dump(exclude_unset=True).items():
        if val is not None and hasattr(settings, field):
            setattr(settings, field, val)

    await db.commit()
    await db.refresh(settings)
    return NotificationPreferencesResponse.model_validate(settings)


@router.get("/watchlists", response_model=WatchlistListResponse, status_code=status.HTTP_200_OK)
async def get_user_watchlists(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List tracked stock price target watchlists for current authenticated user."""
    from sqlalchemy import select
    from app.db.models.market_model import UserStockWatchlistModel

    stmt = select(UserStockWatchlistModel).where(UserStockWatchlistModel.user_id == current_user.user_id)
    items = list((await db.execute(stmt)).scalars().all())
    return WatchlistListResponse(
        total=len(items),
        items=[WatchlistItemSchema.model_validate(item) for item in items],
    )


@router.post("/watchlists", response_model=WatchlistItemSchema, status_code=status.HTTP_201_CREATED)
async def add_user_watchlist(
    payload: WatchlistAddRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add or update a stock target price watchlist item for current user."""
    from sqlalchemy import select
    from app.db.models.market_model import UserStockWatchlistModel
    from app.services.stock_prediction_service import TICKER_TO_COMPANY

    clean_symbol = payload.symbol.strip().upper().replace(".NS", "")
    if clean_symbol not in TICKER_TO_COMPANY:
        from app.core.exceptions import ValidationError
        raise ValidationError("Company not supported. Please select a company from the supported Nifty 50 list.", status_code=400)

    stmt = select(UserStockWatchlistModel).where(
        UserStockWatchlistModel.user_id == current_user.user_id,
        UserStockWatchlistModel.symbol == clean_symbol,
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        item = UserStockWatchlistModel(
            user_id=current_user.user_id,
            symbol=clean_symbol,
            target_high_price=payload.target_high_price,
            target_low_price=payload.target_low_price,
        )
        db.add(item)
    else:
        if payload.target_high_price is not None:
            item.target_high_price = payload.target_high_price
            item.is_above_high = False
        if payload.target_low_price is not None:
            item.target_low_price = payload.target_low_price
            item.is_below_low = False

    await db.commit()
    await db.refresh(item)
    return WatchlistItemSchema.model_validate(item)


@router.delete("/watchlists/{watchlist_id}", status_code=status.HTTP_200_OK)
async def delete_user_watchlist(
    watchlist_id: int = Path(..., description="Watchlist ID to remove"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a stock target price watchlist entry owned by current user."""
    from sqlalchemy import select
    from app.db.models.market_model import UserStockWatchlistModel

    stmt = select(UserStockWatchlistModel).where(
        UserStockWatchlistModel.watchlist_id == watchlist_id,
        UserStockWatchlistModel.user_id == current_user.user_id,
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist entry not found.")

    await db.delete(item)
    await db.commit()
    return {"success": True, "message": "Watchlist entry removed."}
