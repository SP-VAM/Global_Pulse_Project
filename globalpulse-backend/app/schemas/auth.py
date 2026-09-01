"""
Pydantic Schemas for User Authentication & Authorization.
Serializes fields to camelCase for frontend compatibility.
"""
import base64
import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.core.exceptions import ValidationError


class SendOtpRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mobile_number: Optional[str] = Field(None, description="Mobile number with country code e.g. '+918131378262'")
    email: Optional[str] = Field(None, description="Email address for OTP verification")
    target: Optional[str] = Field(None, description="Mobile number or Email address")
    channel: Optional[str] = Field(None, description="Delivery channel: EMAIL or SMS")
    purpose: Optional[str] = Field(None, description="OTP Purpose: EMAIL_VERIFICATION, PHONE_VERIFICATION, PROFILE_CHANGE, etc.")

    @property
    def target_value(self) -> str:
        val = self.target or self.mobile_number or self.email
        if not val or not str(val).strip():
            raise ValidationError("Please enter an email address before requesting email verification.")
        return str(val).strip()


class VerifyOtpRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mobile_number: Optional[str] = Field(None, description="Mobile number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    target: Optional[str] = Field(None, description="Mobile number or Email address")
    channel: Optional[str] = Field(None, description="Delivery channel: EMAIL or SMS")
    purpose: Optional[str] = Field(None, description="OTP Purpose: EMAIL_VERIFICATION, PHONE_VERIFICATION, PROFILE_CHANGE, etc.")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification OTP code")

    @property
    def target_value(self) -> str:
        val = self.target or self.mobile_number or self.email
        if not val:
            raise ValueError("Either mobile_number, email, or target must be provided.")
        return val


class VerifyOtpResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    verification_token: str = Field(..., description="Short-lived token for signup or password reset")
    message: str = Field("Verification code verified successfully.")


class SignupRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = Field(None)
    mobile_number: Optional[str] = Field(None)
    mobileNumber: Optional[str] = Field(None)
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    auth_provider: str = Field("LOCAL")
    verification_token: Optional[str] = Field(None, description="Verification token from OTP step")


class LoginRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    identity: Optional[str] = Field(None, description="Username or email address")
    username: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    identifier: Optional[str] = Field(None)
    password: str = Field(..., description="User password")

    @model_validator(mode="after")
    def validate_identity(self) -> "LoginRequest":
        if not self.identity:
            self.identity = self.username or self.email or self.identifier
        if not self.identity:
            raise ValueError("Username or email address is required.")
        return self


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    identity: str = Field(..., description="Username, email, or mobile number")


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reset_token: str = Field(..., description="Password reset token obtained via OTP verification")
    new_password: str = Field(..., min_length=6, description="New password")


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    current_password: Optional[str] = Field(None, description="Current password for verification")
    new_password: Optional[str] = Field(None, min_length=6, description="New password")
    confirm_password: Optional[str] = Field(None, description="Confirm new password")

    currentPassword: Optional[str] = Field(None)
    newPassword: Optional[str] = Field(None)
    confirmPassword: Optional[str] = Field(None)

    @property
    def current_pass_val(self) -> str:
        return self.current_password or self.currentPassword or ""

    @property
    def new_pass_val(self) -> str:
        return self.new_password or self.newPassword or ""

    @property
    def confirm_pass_val(self) -> str:
        return self.confirm_password or self.confirmPassword or ""


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = Field(None)
    mobile_number: Optional[str] = Field(None)
    mobileNumber: Optional[str] = Field(None)
    first_name: Optional[str] = Field(None)
    firstName: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    lastName: Optional[str] = Field(None)
    profile_image: Optional[str] = Field(None)
    profileImage: Optional[str] = Field(None)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "firstName" in data and "first_name" not in data:
                data["first_name"] = data["firstName"]
            if "lastName" in data and "last_name" not in data:
                data["last_name"] = data["lastName"]
            if "mobileNumber" in data and "mobile_number" not in data:
                data["mobile_number"] = data["mobileNumber"]
            if "profileImage" in data and "profile_image" not in data:
                data["profile_image"] = data["profileImage"]
        return data

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return str(v).strip()

    @field_validator("profile_image")
    @classmethod
    def validate_profile_image(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not str(v).strip():
            return ""
        v_str = str(v).strip()
        if v_str.startswith("data:image/"):
            match = re.match(r"^data:image/(jpeg|jpg|png|webp);base64,(.+)$", v_str, re.IGNORECASE)
            if not match:
                raise ValidationError("Invalid profile image format. Only JPEG, PNG, and WebP images are allowed.")
            b64_data = match.group(2)
            try:
                raw_bytes = base64.b64decode(b64_data)
            except Exception:
                raise ValidationError("Invalid Base64 encoding in profile image payload.")

            if len(raw_bytes) > 2097152:  # 2 MB
                raise ValidationError("Profile image size exceeds maximum allowed limit of 2 MB.")

            is_jpeg = raw_bytes.startswith(b"\xff\xd8\xff")
            is_png = raw_bytes.startswith(b"\x89PNG")
            is_webp = raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16]
            if not (is_jpeg or is_png or is_webp):
                raise ValidationError("Uploaded file is not a valid JPEG, PNG, or WebP image.")
            return v_str
        elif v_str.startswith("http://") or v_str.startswith("https://"):
            return v_str
        else:
            raise ValidationError("Invalid profile image Data URL.")



class UserResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    auth_provider: str
    is_mobile_verified: bool
    is_email_verified: bool
    profile_image: Optional[str] = None
    account_status: str
    last_login_at: Optional[datetime] = None
    created_at: datetime

    @property
    def phone(self) -> Optional[str]:
        return self.mobile_number

    @property
    def phone_number(self) -> Optional[str]:
        return self.mobile_number


class TokenResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    @computed_field
    def accessToken(self) -> str:
        return self.access_token


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    setting_id: int
    user_id: int
    price_alerts: bool = True
    dark_mode: bool = True
    weekly_digest: bool = False
    two_factor_auth: bool = True


class UserSettingsUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    price_alerts: Optional[bool] = Field(None)
    dark_mode: Optional[bool] = Field(None)
    weekly_digest: Optional[bool] = Field(None)
    two_factor_auth: Optional[bool] = Field(None)


class SessionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    session_id: int
    ip_address: Optional[str] = None
    device_name: Optional[str] = None
    created_at: datetime
    last_activity: Optional[datetime] = None
    is_current: bool = False


class SessionListResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total: int
    sessions: List[SessionResponse]



