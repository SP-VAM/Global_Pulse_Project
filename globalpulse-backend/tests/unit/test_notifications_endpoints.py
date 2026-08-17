"""
Integration tests for FastAPI Notification endpoints (/api/v1/notifications).
"""
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.api.v1.dependencies import get_current_active_user
from app.db.models.notification_model import NotificationModel
from app.db.models.user_model import UserModel
from app.main import app


@pytest.fixture
def test_user():
    return UserModel(
        user_id=123,
        email="testuser@globalpulse.test",
        username="testuser",
        is_email_verified=True,
        account_status="ACTIVE",
    )


@pytest.mark.asyncio
async def test_notifications_endpoints_flow(test_user, mocker):
    """Test full HTTP endpoint lifecycle for notifications."""
    app.dependency_overrides[get_current_active_user] = lambda: test_user

    dt_now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    mock_notif = NotificationModel(
        notification_id=10,
        user_id=123,
        title="Test Endpoint Alert",
        message="Endpoint test body",
        notification_type="FINANCIAL",
        is_read=False,
        read_at=None,
        created_at=dt_now,
    )

    mocker.patch(
        "app.services.notification_service.NotificationService.get_user_notifications",
        AsyncMock(return_value=([mock_notif], 1, 1)),
    )
    mocker.patch(
        "app.services.notification_service.NotificationService.get_unread_count",
        AsyncMock(return_value=1),
    )
    mocker.patch(
        "app.services.notification_service.NotificationService.mark_as_read",
        AsyncMock(return_value=mock_notif),
    )
    mocker.patch(
        "app.services.notification_service.NotificationService.mark_all_as_read",
        AsyncMock(return_value=1),
    )
    mocker.patch(
        "app.services.notification_service.NotificationService.register_device_token",
        AsyncMock(return_value=None),
    )
    mocker.patch(
        "app.services.notification_service.NotificationService.deregister_device_token",
        AsyncMock(return_value=True),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/notifications
        r1 = await client.get("/api/v1/notifications")
        assert r1.status_code == 200
        data1 = r1.json()
        assert len(data1["notifications"]) == 1
        assert data1["unread_count"] == 1

        # 2. GET /api/v1/notifications/unread-count
        r2 = await client.get("/api/v1/notifications/unread-count")
        assert r2.status_code == 200
        assert r2.json()["unread_count"] == 1

        # 3. PATCH /api/v1/notifications/10/read
        r3 = await client.patch("/api/v1/notifications/10/read")
        assert r3.status_code == 200
        assert r3.json()["success"] is True

        # 4. PATCH /api/v1/notifications/read-all
        r4 = await client.patch("/api/v1/notifications/read-all")
        assert r4.status_code == 200
        assert r4.json()["updated_count"] == 1

        # 5. POST /api/v1/notifications/device-token
        r5 = await client.post(
            "/api/v1/notifications/device-token",
            json={"fcm_token": "fcm_test_token_sample_12345", "device_type": "WEB"},
        )
        assert r5.status_code == 200
        assert r5.json()["success"] is True

        # 6. DELETE /api/v1/notifications/device-token
        r6 = await client.request(
            "DELETE",
            "/api/v1/notifications/device-token",
            json={"fcm_token": "fcm_test_token_sample_12345"},
        )
        assert r6.status_code == 200
        assert r6.json()["success"] is True

    app.dependency_overrides.clear()
