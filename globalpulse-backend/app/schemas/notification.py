"""
GlobalPulse Pydantic Schemas for FRD-048 Push Notifications and Device Tokens.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    user_id: int
    title: str
    message: str
    notification_type: str = "INFO"
    is_read: bool
    action_url: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    total_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    success: bool
    notification_id: Optional[int] = None
    updated_count: int
    message: str


class DeviceTokenRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, description="FCM device registration token")
    device_type: str = Field(default="WEB", description="Device type: WEB, ANDROID, IOS")


class DeviceTokenDeregisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, description="FCM device registration token to remove")


class SendNotificationRequest(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    notification_type: str = Field(default="INFO", description="FINANCIAL, ACCOUNT, SECURITY, REMINDER, BUDGET_ALERT")
    action_url: Optional[str] = None
    send_push: bool = True
