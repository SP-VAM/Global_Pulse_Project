"""
UserRepository, OtpRepository, SessionRepository, AuditRepository, and UserSettingsRepository.
"""
from datetime import datetime, timezone
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

    async def get_latest_valid_otp(self, target_val: str, otp_code: str) -> Optional[OtpVerificationModel]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(OtpVerificationModel)
            .where(
                (OtpVerificationModel.target_value == target_val) | (OtpVerificationModel.mobile_number == target_val),
                OtpVerificationModel.otp_code == otp_code,
                OtpVerificationModel.is_used == False,
                OtpVerificationModel.expires_at > now,
            )
            .order_by(OtpVerificationModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def mark_as_used(self, otp_id: int) -> None:
        now = datetime.now(timezone.utc)
        stmt = update(OtpVerificationModel).where(OtpVerificationModel.otp_id == otp_id).values(is_used=True, is_verified=True, verified_at=now)
        await self.session.execute(stmt)
        await self.session.commit()



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
