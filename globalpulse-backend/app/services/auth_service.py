"""
Authentication Service.
Coordinates user registration, credential validation, OTP issuance & verification,
password reset, and session tracking.
"""
import hashlib
import logging
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.exceptions import GlobalPulseError, ValidationError, AuthenticationError, ServiceUnavailableError, ConflictError
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.models.user_model import UserModel, UserSessionModel, UserSettingsModel, OtpVerificationModel
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
from app.services.email_service import get_email_service, mask_email
from app.services.sms_service import get_sms_service, normalize_indian_mobile, mask_mobile

_settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.otp_repo = OtpRepository(session)
        self.session_repo = SessionRepository(session)
        self.audit_repo = AuditRepository(session)

    async def send_otp(self, req: SendOtpRequest, authenticated_user_id: Optional[int] = None) -> dict:
        """
        Cryptographically generate and dispatch 6-digit OTP code to email or mobile.
        Stores SHA-256 hash in database with PENDING -> SENT/FAILED transaction-safe lifecycle.
        Enforces server-side 60s cooldown and 3 req / 10 min rate limits.
        """
        raw_target = (req.target_value or "").strip()
        channel = (getattr(req, "channel", None) or ("EMAIL" if "@" in raw_target else "SMS")).upper()
        
        # Target normalization & email requirement validation
        if channel == "EMAIL":
            if not raw_target or "@" not in raw_target or len(raw_target.split("@")) != 2 or not raw_target.split("@")[0] or not raw_target.split("@")[1]:
                raise ValidationError("Please enter an email address before requesting email verification.")
            target = raw_target.lower()
            masked_target = mask_email(target)
        else:
            if not raw_target or not any(c.isdigit() for c in raw_target):
                raise ValidationError("Please enter a valid mobile number before requesting verification.")
            channel = "SMS"
            target = normalize_indian_mobile(raw_target)
            masked_target = mask_mobile(target)

        # Purpose validation against allowlist
        allowed_purposes = {"EMAIL_VERIFICATION", "PHONE_VERIFICATION", "SIGNUP_VERIFICATION", "LOGIN_VERIFICATION", "PASSWORD_RESET", "PROFILE_CHANGE"}
        purpose = (getattr(req, "purpose", None) or ("EMAIL_VERIFICATION" if channel == "EMAIL" else "PHONE_VERIFICATION")).upper()
        if purpose not in allowed_purposes:
            raise ValidationError(f"Invalid OTP purpose: '{purpose}'.")

        # Step 0: Fast-fail if provider credentials are not configured in environment (0ms, 0 DB round-trips)
        if channel == "EMAIL":
            get_email_service().validate_configuration()
        else:
            get_sms_service().validate_configuration()

        # Context ownership check for authenticated user
        if authenticated_user_id:
            user_id = authenticated_user_id
        else:
            existing_user = (
                await self.user_repo.get_by_email(target)
                if channel == "EMAIL"
                else await self.user_repo.get_by_mobile(target)
            )
            user_id = existing_user.user_id if existing_user else None

        # Server-side persistent database rate limiting
        # 1. 60-second cooldown per target+channel+purpose
        recent_cooldown = await self.otp_repo.get_recent_otp_for_cooldown(target, channel, purpose, cooldown_seconds=60)
        if recent_cooldown:
            raise GlobalPulseError(
                message="Resend cooldown active. Please wait 60 seconds before requesting a new verification code.",
                status_code=429,
            )

        # 2. Maximum 3 requests within 10 minutes window
        recent_count = await self.otp_repo.count_recent_otps_in_window(target, channel, purpose, window_minutes=10)
        if recent_count >= 3:
            raise GlobalPulseError(
                message="Too many OTP requests (maximum 3 per 10 minutes). Please try again later.",
                status_code=429,
            )

        # Invalidate previous unverified active OTPs for same target+channel+purpose
        await self.otp_repo.invalidate_active_otps_for_target(target, channel, purpose)

        # Cryptographic 6-digit OTP generation using secrets module
        otp_code = "".join(secrets.choice("0123456789") for _ in range(6))
        otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Step 1: Create PENDING record
        otp_record = await self.otp_repo.create(
            {
                "user_id": user_id,
                "email": target if channel == "EMAIL" else None,
                "mobile_number": target if channel == "SMS" else None,
                "target": target,
                "channel": channel,
                "purpose": purpose,
                "otp_code_hash": otp_hash,
                "otp_type": "EMAIL_VERIFICATION" if channel == "EMAIL" else "MOBILE_VERIFICATION",
                "attempt_count": 0,
                "max_attempts": 5,
                "delivery_status": "PENDING",
                "expires_at": expires,
                "is_verified": False,
            }
        )

        # Step 2: Attempt provider delivery
        try:
            if channel == "EMAIL":
                email_svc = get_email_service()
                email_svc.send_otp_email(recipient_email=target, otp_code=otp_code)
            else:
                sms_svc = get_sms_service()
                await sms_svc.send_sms_otp(recipient_mobile=target, otp_code=otp_code)

            # Step 3: Provider succeeded -> mark SENT
            stmt_upd = (
                update(OtpVerificationModel)
                .where(OtpVerificationModel.otp_id == otp_record.otp_id)
                .values(delivery_status="SENT")
            )
            await self.session.execute(stmt_upd)
            await self.session.commit()
            logger.info("OTP delivery ACCEPTED by %s provider for %s", channel, masked_target)

        except Exception as provider_err:
            # Step 4: Provider failed -> mark FAILED & invalidated
            logger.error("OTP provider delivery FAILED for %s: %s", masked_target, provider_err)
            now = datetime.now(timezone.utc)
            stmt_fail = (
                update(OtpVerificationModel)
                .where(OtpVerificationModel.otp_id == otp_record.otp_id)
                .values(delivery_status="FAILED", invalidated_at=now)
            )
            await self.session.execute(stmt_fail)
            await self.session.commit()

            if isinstance(provider_err, ServiceUnavailableError):
                raise provider_err
            raise ServiceUnavailableError(f"{channel} OTP delivery failed. Please check provider configuration.")

        return {
            "success": True,
            "message": f"Verification code sent to {masked_target}.",
            "expiresIn": 300,
            "resendAfter": 60,
        }

    async def verify_otp(self, req: VerifyOtpRequest, authenticated_user_id: Optional[int] = None) -> VerifyOtpResponse:
        """
        Verify 6-digit OTP code against server-side SHA-256 hash.
        Atomically consumes the OTP and updates user verification state.
        """
        raw_target = req.target_value.strip()
        channel = (getattr(req, "channel", None) or ("EMAIL" if "@" in raw_target else "SMS")).upper()
        
        if channel == "EMAIL" or "@" in raw_target:
            channel = "EMAIL"
            target = raw_target.lower()
        else:
            channel = "SMS"
            target = normalize_indian_mobile(raw_target)

        purpose = (getattr(req, "purpose", None) or ("EMAIL_VERIFICATION" if channel == "EMAIL" else "PHONE_VERIFICATION")).upper()

        # Locate latest valid unverified SENT OTP matching target+channel+purpose
        otp_record = await self.otp_repo.get_latest_valid_otp(target, channel, purpose)
        if not otp_record:
            raise ValidationError("Invalid or expired OTP verification code.")

        # Context ownership check
        if authenticated_user_id and otp_record.user_id and otp_record.user_id != authenticated_user_id:
            raise GlobalPulseError(message="Unauthorized: OTP belongs to another user context.", status_code=403)

        # Hash submitted OTP and compare
        submitted_hash = hashlib.sha256(req.otp_code.strip().encode("utf-8")).hexdigest()
        if submitted_hash != otp_record.otp_code_hash:
            attempts = await self.otp_repo.increment_attempt_count_atomic(otp_record.otp_id)
            remaining = max(0, otp_record.max_attempts - attempts)
            if remaining <= 0:
                raise ValidationError("Too many failed verification attempts (5/5). OTP code has been invalidated.")
            raise ValidationError(f"Invalid OTP code. Remaining attempts: {remaining}")

        # Locate target user if authenticated context is provided
        user_to_update = None
        if authenticated_user_id:
            stmt_u = select(UserModel).where(UserModel.user_id == authenticated_user_id)
            res_u = await self.session.execute(stmt_u)
            user_to_update = res_u.scalar_one_or_none()
        else:
            user_to_update = (
                await self.user_repo.get_by_email(target)
                if channel == "EMAIL"
                else await self.user_repo.get_by_mobile(target)
            )

        # Conflict Pre-Check: BEFORE consuming the OTP, check if another user owns the target value
        if user_to_update:
            if channel == "EMAIL":
                existing_owner = await self.user_repo.get_by_email(target)
                if existing_owner and existing_owner.user_id != user_to_update.user_id:
                    raise ConflictError("This email address is already associated with another account.")
            else:
                existing_owner = await self.user_repo.get_by_mobile(target)
                if existing_owner and existing_owner.user_id != user_to_update.user_id:
                    raise ConflictError("This mobile number is already associated with another account.")

        # Transaction-safe execution of OTP consumption & profile update
        try:
            # Atomically consume OTP to prevent race conditions / double verification
            consumed = await self.otp_repo.consume_otp_atomic(otp_record.otp_id)
            if not consumed:
                raise ValidationError("OTP code has already been consumed.")

            if user_to_update:
                if channel == "EMAIL":
                    if user_to_update.email != target:
                        user_to_update.email = target
                    user_to_update.is_email_verified = True
                else:
                    if user_to_update.mobile_number != target:
                        user_to_update.mobile_number = target
                    user_to_update.is_mobile_verified = True

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            err_str = str(exc).lower()
            if "users_email_key" in err_str or "email" in err_str:
                raise ConflictError("This email address is already associated with another account.")
            elif "users_mobile_number_key" in err_str or "mobile" in err_str:
                raise ConflictError("This mobile number is already associated with another account.")
            else:
                logger.exception("Database integrity error during OTP verification: %s", exc)
                raise GlobalPulseError(message="Database conflict during profile update.", status_code=409)
        except Exception as exc:
            await self.session.rollback()
            raise exc

        # Issue temporary verification token
        ver_token = create_access_token(
            subject=target,
            extra_claims={
                "purpose": purpose,
                "target": target,
                "channel": channel,
                "user_id": user_to_update.user_id if user_to_update else None,
            },
        )
        return VerifyOtpResponse(verification_token=ver_token, message="Verification code verified successfully.")

    async def signup(self, req: SignupRequest, ip: Optional[str] = None, device: Optional[str] = None) -> TokenResponse:
        """Register new user account, create session, and issue JWT tokens."""
        mobile_num = req.mobile_number or getattr(req, "mobileNumber", None)
        if req.verification_token:
            try:
                payload = decode_token(req.verification_token)
                extracted = payload.get("mobile") or payload.get("target") or payload.get("sub")
                if extracted and "@" not in extracted and not mobile_num:
                    mobile_num = extracted
            except Exception:
                pass

        final_email = req.email.strip().lower() if req.email and req.email.strip() else None

        if await self.user_repo.get_by_username(req.username):
            raise ValidationError(f"Username '{req.username}' is already taken.")
        if req.email and await self.user_repo.get_by_email(req.email):
            raise ValidationError(f"Email '{req.email}' is already registered.")
        if mobile_num and await self.user_repo.get_by_mobile(mobile_num):
            raise ValidationError(f"Mobile number '{mobile_num}' is already registered.")

        pw_hash = hash_password(req.password)
        user = await self.user_repo.create(
            {
                "username": req.username,
                "email": final_email,
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
            raise AuthenticationError("Invalid username/email or password.")

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

        # Security notification
        try:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.session)
            await notif_svc.create_and_send_notification(
                user_id=user.user_id,
                title="Security Alert: New Sign-in",
                message=f"Sign-in detected on {device or 'Web Browser'}.",
                notification_type="SECURITY",
                action_url="/dashboard/profile",
                send_push=False,
            )
        except Exception as notif_err:
            logger.debug("Login notification skipped: %s", notif_err)

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

        # Security notification
        try:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.session)
            await notif_svc.create_and_send_notification(
                user_id=user.user_id,
                title="Security Alert: Password Changed",
                message="Your account password was recently changed. If you did not make this request, contact support immediately.",
                notification_type="SECURITY",
                action_url="/dashboard/profile",
                send_push=True,
            )
        except Exception as notif_err:
            logger.debug("Password reset notification skipped: %s", notif_err)

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

        if req.first_name is not None and req.first_name != user.first_name:
            updates["first_name"] = req.first_name

        if req.last_name is not None and req.last_name != user.last_name:
            updates["last_name"] = req.last_name

        if req.profile_image is not None and req.profile_image != user.profile_image:
            updates["profile_image"] = req.profile_image

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


