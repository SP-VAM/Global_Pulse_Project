"""
GlobalPulse Notification & Device Token Repository.
Provides database operations for FRD-048 Push Notifications and Device Tokens.
"""
from datetime import datetime, timezone
import logging
from typing import List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification_model import NotificationModel, UserDeviceTokenModel

logger = logging.getLogger(__name__)


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> List[NotificationModel]:
        """Fetch notifications for a specific user, newest first."""
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)
        if unread_only:
            stmt = stmt.where(NotificationModel.is_read == False)  # noqa: E712
        stmt = stmt.order_by(NotificationModel.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: int) -> int:
        """Return total unread notifications for a user."""
        stmt = (
            select(func.count(NotificationModel.notification_id))
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.is_read == False)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: int, user_id: int) -> Optional[NotificationModel]:
        """
        Mark a single notification as read if owned by user_id.
        Idempotent operation.
        """
        stmt = select(NotificationModel).where(
            NotificationModel.notification_id == notification_id,
            NotificationModel.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        notification = result.scalar_one_or_none()
        if not notification:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(notification)

        return notification

    async def mark_all_as_read(self, user_id: int) -> int:
        """
        Mark all unread notifications as read for a specific user.
        """
        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "INFO",
        action_url: Optional[str] = None,
    ) -> NotificationModel:
        """Create a new notification entry for a user."""
        notification = NotificationModel(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False,
            action_url=action_url,
        )
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def save_device_token(
        self,
        user_id: int,
        fcm_token: str,
        device_type: str = "WEB",
    ) -> UserDeviceTokenModel:
        """Register or update an active FCM device token for push notifications."""
        stmt = select(UserDeviceTokenModel).where(UserDeviceTokenModel.fcm_token == fcm_token)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.user_id = user_id
            existing.device_type = device_type
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        new_token = UserDeviceTokenModel(
            user_id=user_id,
            fcm_token=fcm_token,
            device_type=device_type,
            is_active=True,
        )
        self.session.add(new_token)
        await self.session.commit()
        await self.session.refresh(new_token)
        return new_token

    async def deactivate_device_token(self, user_id: int, fcm_token: str) -> bool:
        """Deactivate or remove a device token on user logout."""
        stmt = (
            update(UserDeviceTokenModel)
            .where(
                UserDeviceTokenModel.user_id == user_id,
                UserDeviceTokenModel.fcm_token == fcm_token,
            )
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_active_device_tokens(self, user_id: int) -> List[str]:
        """Fetch list of active FCM tokens for a user."""
        stmt = select(UserDeviceTokenModel.fcm_token).where(
            UserDeviceTokenModel.user_id == user_id,
            UserDeviceTokenModel.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
