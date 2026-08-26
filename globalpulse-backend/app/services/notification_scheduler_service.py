"""
GlobalPulse Notification Scheduler Service.
Manages periodic background evaluation tasks in FastAPI lifespan setup.
Asynchronous, cancellable during shutdown, exception-safe, database-safe, and idempotent.
"""
import asyncio
import logging
from typing import Optional

from app.db.session import AsyncSessionLocal
from app.services.proactive_notification_service import ProactiveNotificationService

logger = logging.getLogger(__name__)


class NotificationSchedulerService:
    def __init__(self, stock_prediction_service=None, poll_interval_seconds: int = 900) -> None:
        self.stock_prediction_service = stock_prediction_service
        self.poll_interval_seconds = poll_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._is_running = False

    def start(self) -> None:
        """Start background polling loop task."""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[NotificationScheduler] Background notification scheduler started (interval: %ds).", self.poll_interval_seconds)

    async def stop(self) -> None:
        """Gracefully stop background scheduler task on app shutdown."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[NotificationScheduler] Background notification scheduler stopped.")

    async def _run_loop(self) -> None:
        """Main polling loop with per-cycle exception isolation."""
        # Initial brief delay on startup to let DB initialize
        await asyncio.sleep(5)

        while self._is_running:
            try:
                await self.run_evaluation_cycle()
            except asyncio.CancelledError:
                break
            except Exception as cycle_err:
                logger.error("[NotificationScheduler] Evaluation cycle error: %s", cycle_err)

            try:
                await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break

    async def run_evaluation_cycle(self) -> None:
        """
        Single complete evaluation cycle with isolated sub-routine transactions.
        """
        logger.debug("[NotificationScheduler] Starting evaluation cycle...")
        async with AsyncSessionLocal() as session:
            proactive_svc = ProactiveNotificationService(session)

            # 1. Budget Threshold Evaluation for all active users
            try:
                from sqlalchemy import select
                from app.db.models.user_model import UserModel
                users = list((await session.execute(select(UserModel.user_id).where(UserModel.account_status == "ACTIVE"))).scalars().all())

                for user_id in users:
                    try:
                        await proactive_svc.evaluate_user_budget_thresholds(user_id)
                    except Exception as e:
                        logger.debug("[NotificationScheduler] Budget eval error user %d: %s", user_id, e)
                        await session.rollback()

                    try:
                        await proactive_svc.evaluate_monthly_digest(user_id)
                    except Exception as e:
                        logger.debug("[NotificationScheduler] Monthly digest error user %d: %s", user_id, e)
                        await session.rollback()

                await proactive_svc.evaluate_weekly_expense_reminders()

            except Exception as user_loop_err:
                logger.warning("[NotificationScheduler] User budget/digest evaluation warning: %s", user_loop_err)
                await session.rollback()

            # 2. Stock Target & ML & News Evaluation
            if self.stock_prediction_service:
                try:
                    # Get snapshot prices
                    snapshot_data = await self.stock_prediction_service.get_market_snapshot()
                    snapshot_map = {
                        item["symbol"].upper().replace(".NS", ""): float(item["current_price"])
                        for item in snapshot_data
                        if item.get("symbol") and item.get("current_price") is not None
                    }
                    await proactive_svc.evaluate_stock_price_targets(snapshot_map)
                except Exception as stock_err:
                    logger.debug("[NotificationScheduler] Stock price target eval error: %s", stock_err)
                    await session.rollback()

                try:
                    await proactive_svc.evaluate_ml_high_confidence_signals(self.stock_prediction_service)
                except Exception as ml_err:
                    logger.debug("[NotificationScheduler] ML signal eval error: %s", ml_err)
                    await session.rollback()

                try:
                    await proactive_svc.evaluate_news_sentiment_shifts(self.stock_prediction_service)
                except Exception as news_err:
                    logger.debug("[NotificationScheduler] News sentiment eval error: %s", news_err)
                    await session.rollback()

        logger.debug("[NotificationScheduler] Evaluation cycle finished.")
