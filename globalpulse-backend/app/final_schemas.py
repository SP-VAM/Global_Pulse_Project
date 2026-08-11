from typing import Optional

from pydantic import BaseModel, EmailStr


# ==========================================================
# SIGNUP REQUEST
# ==========================================================

class SignupRequest(BaseModel):
    username: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    password: str


# ==========================================================
# LOGIN REQUEST
# ==========================================================

class LoginRequest(BaseModel):
    email: str
    password: str


# ==========================================================
# SEND OTP REQUEST
# ==========================================================

class SendOTPRequest(BaseModel):
    mobile_number: str


# ==========================================================
# VERIFY OTP REQUEST
# ==========================================================

class VerifyOTPRequest(BaseModel):
    identifier: str
    otp_code: str
    purpose: str
    firebase_verified: Optional[bool] = False
    firebase_id_token: Optional[str] = None
# ==========================================================
# GOOGLE LOGIN REQUEST
# ==========================================================

class GoogleLoginRequest(BaseModel):
    access_token: str


# ==========================================================
# FIREBASE LOGIN REQUEST
# ==========================================================

class FirebaseLoginRequest(BaseModel):
    id_token: str
    username: Optional[str] = None


# ==========================================================
# USER RESPONSE
# ==========================================================

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    auth_provider: str
    is_mobile_verified: bool = False
    is_email_verified: bool = False
    account_status: str = "ACTIVE"

    model_config = {
        "from_attributes": True
    }


# ==========================================================
# COMMON RESPONSE
# ==========================================================

class MessageResponse(BaseModel):
    message: str
    user: Optional[UserResponse] = None

# ==========================================================
# COMPLETE PROFILE
# ==========================================================

class CompleteProfileRequest(BaseModel):
    username: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    password: str

# ==========================================================
# LOGOUT REQUEST
# ==========================================================

class LogoutRequest(BaseModel):
    access_token: str

class ForgotPasswordRequest(BaseModel):
    identifier: str

class GoogleSignupCompleteRequest(BaseModel):
    email: str
    username: str
    password: str

class VerifyForgotOTPRequest(BaseModel):
    identifier: str
    otp_code: str

class ResetPasswordRequest(BaseModel):
    identifier: str
    new_password: str

class SendOTPRequest(BaseModel):
    mobile_number: str