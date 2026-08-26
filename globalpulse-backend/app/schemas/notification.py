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
    dedup_key: Optional[str] = None
    payload_json: Optional[str] = None
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


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_alerts: bool = True
    monthly_digest: bool = True
    stock_alerts: bool = True
    ml_alerts: bool = True
    news_alerts: bool = True
    learning_alerts: bool = True
    weekly_reminders: bool = True
    timezone: str = "Asia/Kolkata"


class NotificationPreferencesUpdateRequest(BaseModel):
    budget_alerts: Optional[bool] = None
    monthly_digest: Optional[bool] = None
    stock_alerts: Optional[bool] = None
    ml_alerts: Optional[bool] = None
    news_alerts: Optional[bool] = None
    learning_alerts: Optional[bool] = None
    weekly_reminders: Optional[bool] = None
    timezone: Optional[str] = None


class WatchlistItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    watchlist_id: int
    user_id: int
    symbol: str
    target_high_price: Optional[float] = None
    target_low_price: Optional[float] = None


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    target_high_price: Optional[float] = Field(None, ge=0.0)
    target_low_price: Optional[float] = Field(None, ge=0.0)


class WatchlistListResponse(BaseModel):
    total: int
    items: List[WatchlistItemSchema]

