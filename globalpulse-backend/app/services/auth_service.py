"""
Authentication Service.
Coordinates user registration, credential validation, OTP issuance & verification,
password reset, and session tracking.
"""
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.exceptions import GlobalPulseError, ValidationError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from sqlalchemy import select
from app.db.models.user_model import UserModel, UserSessionModel, UserSettingsModel
from app.repositories.user_repository import AuditRepository, OtpRepository, SessionRepository, UserRepository
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services.email_service import get_email_service

_settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.otp_repo = OtpRepository(session)
        self.session_repo = SessionRepository(session)
        self.audit_repo = AuditRepository(session)

    async def send_otp(self, req: SendOtpRequest) -> dict:
        """Generate and save 6-digit OTP code valid for 5 minutes.

        In development mode (APP_ENV=development) the OTP code is returned
        in the response body for local testing. In all other environments
        only a confirmation message is returned so the secret is never
        exposed over the network.
        """
        target = req.target_value
        code = f"{random.randint(100000, 999999)}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Check if user exists (by email, mobile, or identity)
        existing_user = (
            await self.user_repo.get_by_mobile(target)
            or await self.user_repo.get_by_email(target)
            or await self.user_repo.get_by_identity(target)
        )
        user_id = existing_user.user_id if existing_user else None

        otp_type = "EMAIL_VERIFICATION" if "@" in target else "MOBILE_VERIFICATION"

        # Create OTP record
        await self.otp_repo.create(
            {
                "user_id": user_id,
                "target_value": target,
                "mobile_number": target if "@" not in target else None,
                "otp_code": code,
                "otp_type": otp_type,
                "expires_at": expires,
                "is_used": False,
                "is_verified": False,
            }
        )

        logger.info("========== [DEV OTP CODE] Target: %s | OTP: %s ==========", target, code)

        if "@" in target:
            try:
                email_svc = get_email_service()
                email_svc.send_otp_email(recipient_email=target, otp_code=code)
            except Exception as mail_err:
                logger.error("Failed to send OTP email: %s", mail_err)

        response: dict = {"message": f"Verification code sent to {target}."}

        # Only expose OTP in development — never in staging or production
        if _settings.APP_ENV == "development":
            response["otpCode"] = code

        return response

    async def verify_otp(self, req: VerifyOtpRequest) -> VerifyOtpResponse:
        """Verify 6-digit OTP code and return short-lived verification token."""
        target = req.target_value
        otp_record = await self.otp_repo.get_latest_valid_otp(target, req.otp_code)
        if not otp_record:
            raise ValidationError("Invalid or expired OTP verification code.")

        await self.otp_repo.mark_as_used(otp_record.otp_id)

        # Issue temporary verification token
        ver_token = create_access_token(
            subject=target, extra_claims={"purpose": "otp_verification", "target": target, "mobile": target}
        )
        return VerifyOtpResponse(verification_token=ver_token, message="Verification code verified successfully.")

    async def signup(self, req: SignupRequest, ip: Optional[str] = None, device: Optional[str] = None) -> TokenResponse:
        """Register new user account, create session, and issue JWT tokens."""
        # Check duplicate username/email
        if await self.user_repo.get_by_username(req.username):
            raise ValidationError(f"Username '{req.username}' is already taken.")
        if await self.user_repo.get_by_email(req.email):
            raise ValidationError(f"Email '{req.email}' is already registered.")

        # If verification_token present and mobile_number is missing, extract mobile/target from token
        mobile_num = req.mobile_number
        if req.verification_token:
            try:
                payload = decode_token(req.verification_token)
                extracted = payload.get("mobile") or payload.get("target") or payload.get("sub")
                if extracted and "@" not in extracted and not mobile_num:
                    mobile_num = extracted
            except Exception:
                pass

        if mobile_num and await self.user_repo.get_by_mobile(mobile_num):
            raise ValidationError(f"Mobile number '{mobile_num}' is already registered.")

        pw_hash = hash_password(req.password)
        user = await self.user_repo.create(
            {
                "username": req.username,
                "email": req.email,
                "mobile_number": mobile_num,
                "password_hash": pw_hash,
                "auth_provider": req.auth_provider,
                "is_mobile_verified": True if req.verification_token else False,
                "is_email_verified": False,
                "account_status": "ACTIVE",
            }
        )

        # Issue final tokens before creating session (avoid double token generation)
        access = create_access_token(user.user_id)
        user_sess = await self.session_repo.create(
            {
                "user_id": user.user_id,
                "access_token": access,
                "ip_address": ip,
                "device_name": device,
                "is_active": True,
            }
        )

        # Re-issue with session_id embedded in claims
        access = create_access_token(user.user_id, {"session_id": user_sess.session_id})
        refresh = create_refresh_token(user.user_id, user_sess.session_id)

        user_sess.access_token = access
        user_sess.refresh_token = refresh
        await self.session.commit()

        # Audit log
        await self.audit_repo.create(
            {"user_id": user.user_id, "table_name": "users", "action": "USER_CREATED", "description": "New account registered."}
        )

        return TokenResponse(access_token=access, user=UserResponse.model_validate(user))

    async def login(self, req: LoginRequest, ip: Optional[str] = None, device: Optional[str] = None) -> TokenResponse:
        """Authenticate user credentials and issue active session tokens."""
        user = await self.user_repo.get_by_identity(req.identity)
        if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
            raise ValidationError("Invalid username/email or password.")

        if user.account_status != "ACTIVE":
            raise ValidationError("Account is inactive or suspended.")

        # Issue tokens before creating session (avoid double token generation)
        access = create_access_token(user.user_id)
        user_sess = await self.session_repo.create(
            {
                "user_id": user.user_id,
                "access_token": access,
                "ip_address": ip,
                "device_name": device,
                "is_active": True,
            }
        )

        # Re-issue with session_id embedded in claims
        access = create_access_token(user.user_id, {"session_id": user_sess.session_id})
        refresh = create_refresh_token(user.user_id, user_sess.session_id)

        user_sess.access_token = access
        user_sess.refresh_token = refresh
        await self.session.commit()

        # Audit log
        await self.audit_repo.create(
            {"user_id": user.user_id, "table_name": "users", "action": "USER_LOGIN", "description": "User logged in."}
        )

        return TokenResponse(access_token=access, user=UserResponse.model_validate(user))

    async def forgot_password(self, req: ForgotPasswordRequest) -> dict:
        """Send password reset code.

        The reset OTP code is only returned in the response body when
        APP_ENV=development.  In staging/production only a confirmation
        message is returned to prevent enumeration and code leakage.
        """
        user = await self.user_repo.get_by_identity(req.identity)
        if not user:
            # Prevent account enumeration — always return the same message
            return {"message": "If account exists, password reset instructions have been sent."}

        code = f"{random.randint(100000, 999999)}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        await self.otp_repo.create(
            {
                "user_id": user.user_id,
                "mobile_number": user.mobile_number or user.email,
                "otp_code": code,
                "expires_at": expires,
                "is_used": False,
            }
        )

        logger.info("========== [DEV RESET CODE] Identity: %s | OTP: %s ==========", req.identity, code)

        response: dict = {"message": "If account exists, password reset instructions have been sent."}

        # Only expose reset code in development — never in staging or production
        if _settings.APP_ENV == "development":
            response["resetCode"] = code

        return response

    async def reset_password(self, req: ResetPasswordRequest) -> dict:
        """Reset password using a verified OTP reset token.

        The reset_token is the short-lived JWT issued by verify_otp().
        We decode it to extract the mobile/identity, find the user, and
        persist the new bcrypt-hashed password.
        """
        try:
            payload = decode_token(req.reset_token)
        except GlobalPulseError as exc:
            raise ValidationError("Invalid or expired password reset token.") from exc

        # Extract mobile or subject from token claims
        mobile = payload.get("mobile") or payload.get("sub")
        if not mobile:
            raise ValidationError("Invalid password reset token: missing identity.")

        # Look up the user by mobile, then by identity (email/username)
        user = await self.user_repo.get_by_mobile(mobile)
        if not user:
            user = await self.user_repo.get_by_identity(mobile)
        if not user:
            raise ValidationError("Account not found for this reset token.")

        # Persist the new password hash
        pw_hash = hash_password(req.new_password)
        await self.user_repo.update(user.user_id, {"password_hash": pw_hash})

        # Revoke all active sessions so old tokens cannot be reused
        await self.session_repo.revoke_all_user_sessions(user.user_id)

        # Audit log
        await self.audit_repo.create(
            {
                "user_id": user.user_id,
                "table_name": "users",
                "action": "PASSWORD_RESET",
                "description": "Password reset successfully.",
            }
        )

        return {"message": "Password has been reset successfully. Please log in with your new password."}

    async def update_profile(self, user_id: int, req: UpdateProfileRequest) -> UserResponse:
        """Update authenticated user profile fields."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("User account not found.")

        updates = {}
        if req.username and req.username != user.username:
            existing = await self.user_repo.get_by_username(req.username)
            if existing and existing.user_id != user_id:
                raise ValidationError(f"Username '{req.username}' is already taken.")
            updates["username"] = req.username

        if req.email and req.email != user.email:
            existing = await self.user_repo.get_by_email(req.email)
            if existing and existing.user_id != user_id:
                raise ValidationError(f"Email '{req.email}' is already registered.")
            updates["email"] = req.email

        if req.mobile_number and req.mobile_number != user.mobile_number:
            existing = await self.user_repo.get_by_mobile(req.mobile_number)
            if existing and existing.user_id != user_id:
                raise ValidationError(f"Mobile number '{req.mobile_number}' is already registered.")
            updates["mobile_number"] = req.mobile_number
            updates["is_mobile_verified"] = True

        if updates:
            updated_user = await self.user_repo.update(user_id, updates)
            await self.audit_repo.create(
                {
                    "user_id": user_id,
                    "table_name": "users",
                    "action": "PROFILE_UPDATED",
                    "description": f"Updated fields: {list(updates.keys())}",
                }
            )
            return UserResponse.model_validate(updated_user)

        return UserResponse.model_validate(user)

    async def get_user_settings(self, user_id: int) -> UserSettingsModel:
        """Fetch or create default settings for user."""
        stmt = select(UserSettingsModel).where(UserSettingsModel.user_id == user_id)
        res = await self.session.execute(stmt)
        settings_obj = res.scalar_one_or_none()
        if not settings_obj:
            settings_obj = UserSettingsModel(
                user_id=user_id,
                price_alerts=True,
                dark_mode=True,
                weekly_digest=False,
                two_factor_auth=True,
            )
            self.session.add(settings_obj)
            await self.session.commit()
            await self.session.refresh(settings_obj)
        return settings_obj

    async def update_user_settings(self, user_id: int, req_data: dict) -> UserSettingsModel:
        """Update settings for authenticated user."""
        settings_obj = await self.get_user_settings(user_id)
        for field in ["price_alerts", "dark_mode", "weekly_digest", "two_factor_auth"]:
            if field in req_data and req_data[field] is not None:
                setattr(settings_obj, field, req_data[field])

        await self.session.commit()
        await self.session.refresh(settings_obj)

        await self.audit_repo.create(
            {
                "user_id": user_id,
                "table_name": "user_settings",
                "action": "SETTINGS_UPDATED",
                "description": f"Updated preferences: {req_data}",
            }
        )
        return settings_obj


