"""
GlobalPulse Notification Service.
Business logic for FRD-048 Push Notifications, Read/Unread State, and Firebase FCM Delivery.
"""
from datetime import datetime
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.notification_model import NotificationModel
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[List[NotificationModel], int, int]:
        """
        Returns (notifications, unread_count, total_count) for the authenticated user.
        """
        notifications = await self.repo.get_user_notifications(
            user_id=user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )
        unread_count = await self.repo.get_unread_count(user_id)
        total_count = len(notifications)
        return notifications, unread_count, total_count

    async def get_unread_count(self, user_id: int) -> int:
        """Get authoritative unread count for user."""
        return await self.repo.get_unread_count(user_id)

    async def mark_as_read(self, notification_id: int, user_id: int) -> NotificationModel:
        """
        Mark a notification as read with ownership validation.
        Raises NotFoundError if the notification does not exist or belongs to another user.
        """
        notification = await self.repo.mark_as_read(notification_id=notification_id, user_id=user_id)
        if not notification:
            raise NotFoundError(f"Notification with id {notification_id} not found.")
        return notification

    async def mark_all_as_read(self, user_id: int) -> int:
        """
        Mark all unread notifications as read for current user.
        Returns count of updated records.
        """
        return await self.repo.mark_all_as_read(user_id=user_id)

    async def delete_read_notifications(self, user_id: int) -> int:
        """
        Delete all read notifications for current user.
        Returns count of deleted records.
        """
        return await self.repo.delete_read_notifications(user_id=user_id)

    async def register_device_token(
        self,
        user_id: int,
        fcm_token: str,
        device_type: str = "WEB",
    ) -> None:
        """Save/update active FCM device token for push notifications."""
        await self.repo.save_device_token(
            user_id=user_id,
            fcm_token=fcm_token,
            device_type=device_type,
        )

    async def deregister_device_token(self, user_id: int, fcm_token: str) -> bool:
        """Deactivate FCM device token on logout."""
        return await self.repo.deactivate_device_token(user_id=user_id, fcm_token=fcm_token)

    async def create_and_send_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "INFO",
        action_url: Optional[str] = None,
        send_push: bool = True,
        dedup_key: Optional[str] = None,
        payload_json: Optional[str] = None,
    ) -> Optional[NotificationModel]:
        """
        Create notification record in PostgreSQL and optionally dispatch real-time FCM push notification.
        """
        # 1. Persist to PostgreSQL
        notification = await self.repo.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            dedup_key=dedup_key,
            payload_json=payload_json,
        )

        # 2. Dispatch real-time push via Firebase Cloud Messaging if enabled
        if notification and send_push:
            try:
                tokens = await self.repo.get_active_device_tokens(user_id)
                if tokens:
                    await self._send_fcm_push(tokens, title, message, notification_type, action_url)
            except Exception as push_err:
                logger.warning("[FCM Push Warning] Failed to dispatch push notification: %s", push_err)

        return notification

    async def _send_fcm_push(
        self,
        tokens: List[str],
        title: str,
        message: str,
        notification_type: str,
        action_url: Optional[str] = None,
    ) -> None:
        """Helper to send Firebase Cloud Messaging multicast push notification."""
        try:
            import firebase_admin
            from firebase_admin import messaging

            # Check if firebase is initialized
            if not firebase_admin._apps:
                from app.firebase_config import initialize_firebase
                initialize_firebase()

            fcm_message = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(
                    title=title,
                    body=message,
                ),
                data={
                    "type": notification_type,
                    "action_url": action_url or "/dashboard",
                    "timestamp": str(int(datetime.utcnow().timestamp())),
                },
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=message,
                        icon="/icon-dark-32x32.png",
                    ),
                    fcm_options=messaging.WebpushFCMOptions(
                        link=action_url or "/dashboard",
                    ),
                ),
            )
            response = messaging.send_each_for_multicast(fcm_message)
            logger.info(
                "[FCM Push] Sent multicast message: %d success, %d failure",
                response.success_count,
                response.failure_count,
            )
        except Exception as err:
            logger.debug("[FCM Push] Push delivery skipped/failed: %s", err)
