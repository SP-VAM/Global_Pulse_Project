"""
Pydantic Schemas for User Authentication & Authorization.
Serializes fields to camelCase for frontend compatibility.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, model_validator
from pydantic.alias_generators import to_camel


class SendOtpRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mobile_number: Optional[str] = Field(None, description="Mobile number with country code e.g. '+918131378262'")
    email: Optional[EmailStr] = Field(None, description="Email address for OTP verification")
    target: Optional[str] = Field(None, description="Mobile number or Email address")

    @property
    def target_value(self) -> str:
        val = self.target or self.mobile_number or self.email
        if not val:
            raise ValueError("Either mobile_number, email, or target must be provided.")
        return val


class VerifyOtpRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    mobile_number: Optional[str] = Field(None, description="Mobile number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    target: Optional[str] = Field(None, description="Mobile number or Email address")
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
    password: str = Field(..., min_length=8)
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
    new_password: str = Field(..., min_length=8, description="New password")


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = Field(None)
    mobile_number: Optional[str] = Field(None)
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    profile_image: Optional[str] = Field(None)


class UserResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    user_id: int
    username: Optional[str] = None
    email: str
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


