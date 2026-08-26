"""
UserRepository, OtpRepository, SessionRepository, AuditRepository, and UserSettingsRepository.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_model import (
    AuditLogModel,
    OtpVerificationModel,
    SocialLoginModel,
    UserModel,
    UserSessionModel,
    UserSettingsModel,
)
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserModel, session)

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.username == username)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_mobile(self, mobile_number: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.mobile_number == mobile_number)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_identity(self, identity: str) -> Optional[UserModel]:
        """Find user by either username or email."""
        stmt = select(UserModel).where((UserModel.username == identity) | (UserModel.email == identity))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


class OtpRepository(BaseRepository[OtpVerificationModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OtpVerificationModel, session)

    async def get_recent_otp_for_cooldown(self, target: str, channel: str, purpose: str, cooldown_seconds: int = 60) -> Optional[OtpVerificationModel]:
        """Check if an active OTP was issued for target+channel+purpose within the last cooldown_seconds."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        stmt = (
            select(OtpVerificationModel)
            .where(
                (OtpVerificationModel.target == target) | (OtpVerificationModel.email == target) | (OtpVerificationModel.mobile_number == target),
                OtpVerificationModel.channel == channel,
                OtpVerificationModel.purpose == purpose,
                OtpVerificationModel.created_at >= cutoff,
                OtpVerificationModel.invalidated_at.is_(None),
            )
            .order_by(OtpVerificationModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def count_recent_otps_in_window(self, target: str, channel: str, purpose: str, window_minutes: int = 10) -> int:
        """Count OTP requests for target+channel+purpose within window_minutes to enforce 3 req / 10 min rate limit."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        stmt = (
            select(OtpVerificationModel)
            .where(
                (OtpVerificationModel.target == target) | (OtpVerificationModel.email == target) | (OtpVerificationModel.mobile_number == target),
                OtpVerificationModel.channel == channel,
                OtpVerificationModel.purpose == purpose,
                OtpVerificationModel.created_at >= cutoff,
            )
        )
        res = await self.session.execute(stmt)
        return len(res.scalars().all())

    async def invalidate_active_otps_for_target(self, target: str, channel: str, purpose: str) -> None:
        """Invalidate previous unverified active OTPs when issuing a new OTP."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(OtpVerificationModel)
            .where(
                (OtpVerificationModel.target == target) | (OtpVerificationModel.email == target) | (OtpVerificationModel.mobile_number == target),
                OtpVerificationModel.channel == channel,
                OtpVerificationModel.purpose == purpose,
                OtpVerificationModel.is_verified == False,
                OtpVerificationModel.invalidated_at.is_(None),
            )
            .values(invalidated_at=now)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_latest_valid_otp(self, target: str, channel: str, purpose: str) -> Optional[OtpVerificationModel]:
        """Find latest unverified, unexpired, non-invalidated SENT OTP matching target+channel+purpose."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(OtpVerificationModel)
            .where(
                (OtpVerificationModel.target == target) | (OtpVerificationModel.email == target) | (OtpVerificationModel.mobile_number == target),
                OtpVerificationModel.channel == channel,
                OtpVerificationModel.purpose == purpose,
                OtpVerificationModel.is_verified == False,
                OtpVerificationModel.invalidated_at.is_(None),
                OtpVerificationModel.delivery_status == "SENT",
                OtpVerificationModel.expires_at > now,
                OtpVerificationModel.attempt_count < OtpVerificationModel.max_attempts,
            )
            .order_by(OtpVerificationModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def increment_attempt_count_atomic(self, otp_id: int) -> int:
        """Atomically increment failed verification attempt_count and invalidate if max_attempts reached."""
        now = datetime.now(timezone.utc)
        # Fetch current count
        stmt_sel = select(OtpVerificationModel).where(OtpVerificationModel.otp_id == otp_id)
        res = await self.session.execute(stmt_sel)
        otp_rec = res.scalar_one_or_none()
        if not otp_rec:
            return 5
        new_count = otp_rec.attempt_count + 1
        values = {"attempt_count": new_count}
        if new_count >= otp_rec.max_attempts:
            values["invalidated_at"] = now

        stmt_upd = update(OtpVerificationModel).where(OtpVerificationModel.otp_id == otp_id).values(**values)
        await self.session.execute(stmt_upd)
        await self.session.commit()
        return new_count

    async def consume_otp_atomic(self, otp_id: int) -> bool:
        """Atomically consume OTP so exactly ONE concurrent request can succeed."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(OtpVerificationModel)
            .where(
                OtpVerificationModel.otp_id == otp_id,
                OtpVerificationModel.is_verified == False,
                OtpVerificationModel.invalidated_at.is_(None),
            )
            .values(is_verified=True, verified_at=now, delivery_status="CONSUMED")
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0



class SessionRepository(BaseRepository[UserSessionModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserSessionModel, session)

    async def get_active_session(self, user_id: int, session_id: int) -> Optional[UserSessionModel]:
        stmt = select(UserSessionModel).where(
            UserSessionModel.session_id == session_id,
            UserSessionModel.user_id == user_id,
            UserSessionModel.is_active == True,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all_active_user_sessions(self, user_id: int) -> List[UserSessionModel]:
        stmt = (
            select(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.is_active == True,
            )
            .order_by(UserSessionModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def revoke_session(self, session_id: int) -> None:
        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.session_id == session_id)
            .values(is_active=False, logout_time=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def revoke_all_user_sessions(self, user_id: int) -> None:
        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.user_id == user_id, UserSessionModel.is_active == True)
            .values(is_active=False, logout_time=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()


class AuditRepository(BaseRepository[AuditLogModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLogModel, session)

    async def get_user_activity(self, user_id: int, limit: int = 20) -> List[AuditLogModel]:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class UserSettingsRepository(BaseRepository[UserSettingsModel, Any, Any]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserSettingsModel, session)

    async def get_by_user_id(self, user_id: int) -> Optional[UserSettingsModel]:
        stmt = select(UserSettingsModel).where(UserSettingsModel.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
