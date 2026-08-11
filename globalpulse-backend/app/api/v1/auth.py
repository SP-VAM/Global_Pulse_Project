"""
FastAPI Authentication & User Management Endpoints.
Prefix: /auth
Rate-limited: all endpoints are throttled to prevent brute-force and OTP spam.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.db.models.user_model import UserModel
from app.db.session import get_db_session
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

_settings = get_settings()


@router.post("/send-otp", status_code=status.HTTP_200_OK)
@limiter.limit(_settings.RATE_LIMIT_AUTH)
async def send_otp(request: Request, req: SendOtpRequest, db: AsyncSession = Depends(get_db_session)):
    """Send 6-digit OTP code to mobile number.

    In development mode the OTP is also returned in the response body.
    In staging/production only a confirmation message is returned.
    """
    service = AuthService(db)
    return await service.send_otp(req)


@router.post("/verify-otp", response_model=VerifyOtpResponse, status_code=status.HTTP_200_OK)
@limiter.limit(_settings.RATE_LIMIT_AUTH)
async def verify_otp(request: Request, req: VerifyOtpRequest, db: AsyncSession = Depends(get_db_session)):
    """Verify 6-digit OTP code."""
    service = AuthService(db)
    return await service.verify_otp(req)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_settings.RATE_LIMIT_AUTH)
async def signup(
    req: SignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user_agent: Annotated[str | None, Header()] = None,
):
    """Register new user account and issue JWT tokens."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    return await service.signup(req, ip=client_ip, device=user_agent)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit(_settings.RATE_LIMIT_AUTH)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user_agent: Annotated[str | None, Header()] = None,
):
    """Authenticate user credentials and issue active JWT tokens."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    return await service.login(req, ip=client_ip, device=user_agent)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit(_settings.RATE_LIMIT_AUTH)
async def forgot_password(request: Request, req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db_session)):
    """Initiate password recovery.

    In development mode the reset code is also returned in the response body.
    In staging/production only a generic confirmation is returned.
    """
    service = AuthService(db)
    return await service.forgot_password(req)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit(_settings.RATE_LIMIT_AUTH)
async def reset_password(request: Request, req: ResetPasswordRequest, db: AsyncSession = Depends(get_db_session)):
    """Reset password using verification token."""
    service = AuthService(db)
    return await service.reset_password(req)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(current_user: UserModel = Depends(get_current_active_user)):
    """Return profile metadata for the authenticated user."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_me(
    req: UpdateProfileRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update profile metadata (username, email, mobileNumber) for authenticated user."""
    service = AuthService(db)
    return await service.update_profile(current_user.user_id, req)


@router.get("/settings", response_model=UserSettingsResponse, status_code=status.HTTP_200_OK)
async def get_settings(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch preferences for the authenticated user."""
    service = AuthService(db)
    return await service.get_user_settings(current_user.user_id)


@router.put("/settings", response_model=UserSettingsResponse, status_code=status.HTTP_200_OK)
async def update_settings(
    req: UserSettingsUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update preferences for the authenticated user."""
    service = AuthService(db)
    updated = await service.update_user_settings(current_user.user_id, req.model_dump(exclude_unset=True))
    return UserSettingsResponse.model_validate(updated)


