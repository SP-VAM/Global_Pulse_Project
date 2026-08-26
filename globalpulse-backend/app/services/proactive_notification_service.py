"""
GlobalPulse Proactive Financial Intelligence Notification Engine.
Business logic for:
  1. BUDGET_THRESHOLD_80 & BUDGET_THRESHOLD_90
  2. MONTHLY_FINANCIAL_DIGEST (1st of month)
  3. STOCK_PRICE_TARGET (Target High/Low crossing & re-arming)
  4. ML_HIGH_CONFIDENCE_SIGNAL (>85% UP signal for tracked stocks)
  5. NEWS_SENTIMENT_SHIFT (Transitions to HIGHLY BULLISH or BEARISH)
  6. LEARNING_MODULE_COMPLETED
  7. WEEKLY_EXPENSE_REMINDER (Sunday evening check for 0 weekly expenses)

Strictly isolated per user, timezone-aware, and guarded by database-backed idempotency.
"""
from datetime import date, datetime, timedelta, timezone
import json
import logging
from typing import Dict, List, Optional
import zoneinfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.expense_model import BudgetModel, ExpenseCategoryModel, ExpenseModel, IncomeModel
from app.db.models.market_model import UserStockWatchlistModel
from app.db.models.learning_model import UserLearningProgressModel
from app.db.models.user_model import UserModel, UserSettingsModel
from app.services.notification_service import NotificationService
from app.services.stock_prediction_service import StockPredictionService

logger = logging.getLogger(__name__)


class ProactiveNotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notif_svc = NotificationService(session)

    async def get_user_settings(self, user_id: int) -> UserSettingsModel:
        """Fetch or create default user settings for preference toggles and timezone."""
        stmt = select(UserSettingsModel).where(UserSettingsModel.user_id == user_id)
        settings = (await self.session.execute(stmt)).scalar_one_or_none()
        if not settings:
            settings = UserSettingsModel(user_id=user_id)
            self.session.add(settings)
            await self.session.commit()
            await self.session.refresh(settings)
        return settings

    # ---------------------------------------------------------------------------
    # 1. BUDGET THRESHOLD WARNINGS (80% & 90%)
    # ---------------------------------------------------------------------------
    async def evaluate_user_budget_thresholds(self, user_id: int) -> int:
        """
        Evaluate budget spending for active budgets of user_id.
        Triggers BUDGET_THRESHOLD_80 and BUDGET_THRESHOLD_90 with strict deduplication.
        """
        settings = await self.get_user_settings(user_id)
        if not settings.budget_alerts:
            return 0

        now_utc = datetime.now(timezone.utc)
        period_str = now_utc.strftime("%Y-%m")
        year, month = now_utc.year, now_utc.month

        # Fetch active budgets for month
        stmt = select(BudgetModel).where(
            BudgetModel.user_id == user_id,
            BudgetModel.budget_year == year,
            BudgetModel.budget_month == month,
        )
        budgets = list((await self.session.execute(stmt)).scalars().all())
        if not budgets:
            return 0

        # Fetch all expenses for this user in month
        exp_stmt = select(ExpenseModel).where(
            ExpenseModel.user_id == user_id,
            func.extract("year", ExpenseModel.expense_date) == year,
            func.extract("month", ExpenseModel.expense_date) == month,
        )
        expenses = list((await self.session.execute(exp_stmt)).scalars().all())

        # Map spent per category
        spent_map: Dict[int, float] = {}
        for exp in expenses:
            cat_id = exp.category_id
            spent_map[cat_id] = spent_map.get(cat_id, 0.0) + float(exp.amount)

        dispatched = 0
        for budget in budgets:
            limit = float(budget.budget_amount)
            if limit <= 0:
                continue

            cat_id = budget.category_id
            spent = spent_map.get(cat_id, 0.0)
            pct = (spent / limit) * 100.0

            # Get Category Name
            cat_stmt = select(ExpenseCategoryModel.category_name).where(ExpenseCategoryModel.category_id == cat_id)
            cat_name = (await self.session.execute(cat_stmt)).scalar_one_or_none() or "Category"

            # 90% Threshold Alert
            if pct >= 90.0:
                dedup = f"budget:{user_id}:{cat_id}:{period_str}:90"
                rem = max(0.0, limit - spent)
                title = f"Budget Warning: 90% Spent ({cat_name})"
                msg = f"You have spent {pct:.1f}% of your {cat_name} budget. Only ₹{rem:,.2f} remains for this month."
                n = await self.notif_svc.create_and_send_notification(
                    user_id=user_id,
                    title=title,
                    message=msg,
                    notification_type="BUDGET_THRESHOLD_90",
                    action_url="/dashboard/expense-tracker",
                    send_push=True,
                    dedup_key=dedup,
                )
                if n:
                    dispatched += 1

            # 80% Threshold Alert
            elif pct >= 80.0:
                dedup = f"budget:{user_id}:{cat_id}:{period_str}:80"
                title = f"Budget Warning: 80% Spent ({cat_name})"
                msg = f"You have spent {pct:.1f}% of your {cat_name} budget. ₹{spent:,.2f} of ₹{limit:,.2f} has been used."
                n = await self.notif_svc.create_and_send_notification(
                    user_id=user_id,
                    title=title,
                    message=msg,
                    notification_type="BUDGET_THRESHOLD_80",
                    action_url="/dashboard/expense-tracker",
                    send_push=True,
                    dedup_key=dedup,
                )
                if n:
                    dispatched += 1

        return dispatched

    # ---------------------------------------------------------------------------
    # 2. MONTHLY FINANCIAL DIGEST (1st of Month)
    # ---------------------------------------------------------------------------
    async def evaluate_monthly_digest(self, user_id: int) -> Optional[int]:
        """
        Generate monthly financial digest on 1st of month for previous month.
        """
        settings = await self.get_user_settings(user_id)
        if not settings.monthly_digest:
            return None

        # User Timezone calculation
        tz_name = settings.timezone or "Asia/Kolkata"
        try:
            user_tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            user_tz = zoneinfo.ZoneInfo("Asia/Kolkata")

        now_user = datetime.now(user_tz)
        if now_user.day != 1:
            return None

        # Previous Month calculation
        first_of_current = date(now_user.year, now_user.month, 1)
        last_day_prev = first_of_current - timedelta(days=1)
        prev_year, prev_month = last_day_prev.year, last_day_prev.month
        month_name = last_day_prev.strftime("%B %Y")

        dedup = f"monthly_digest:{user_id}:{prev_year}-{prev_month:02d}"

        # Fetch Previous Month's Income
        inc_stmt = select(func.sum(IncomeModel.amount)).where(
            IncomeModel.user_id == user_id,
            func.extract("year", IncomeModel.income_date) == prev_year,
            func.extract("month", IncomeModel.income_date) == prev_month,
        )
        total_income = float((await self.session.execute(inc_stmt)).scalar() or 0.0)

        # Fetch Previous Month's Expenses
        exp_stmt = select(func.sum(ExpenseModel.amount)).where(
            ExpenseModel.user_id == user_id,
            func.extract("year", ExpenseModel.expense_date) == prev_year,
            func.extract("month", ExpenseModel.expense_date) == prev_month,
        )
        total_expenses = float((await self.session.execute(exp_stmt)).scalar() or 0.0)

        net_savings = total_income - total_expenses

        title = f"Your {month_name} Financial Summary"
        msg = f"Income: ₹{total_income:,.2f} | Expenses: ₹{total_expenses:,.2f} | Net Savings: ₹{net_savings:,.2f}"

        payload = {
            "period": f"{prev_year}-{prev_month:02d}",
            "month_name": month_name,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
        }

        notif = await self.notif_svc.create_and_send_notification(
            user_id=user_id,
            title=title,
            message=msg,
            notification_type="MONTHLY_FINANCIAL_DIGEST",
            action_url="/dashboard/expense-tracker",
            send_push=True,
            dedup_key=dedup,
            payload_json=json.dumps(payload),
        )
        return 1 if notif else 0

    # ---------------------------------------------------------------------------
    # 3. STOCK PRICE TARGET ALERTS (High/Low Crossing & Re-arming)
    # ---------------------------------------------------------------------------
    async def evaluate_stock_price_targets(self, snapshot_map: Dict[str, float]) -> int:
        """
        Evaluate user watchlists against live snapshot prices.
        Triggers STOCK_PRICE_TARGET on exact price target crossing and re-arms when price retreats.
        """
        if not snapshot_map:
            return 0

        stmt = select(UserStockWatchlistModel)
        watchlists = list((await self.session.execute(stmt)).scalars().all())

        today_str = date.today().isoformat()
        dispatched = 0

        for w in watchlists:
            settings = await self.get_user_settings(w.user_id)
            if not settings.stock_alerts:
                continue

            symbol = w.symbol.upper().replace(".NS", "")
            current_price = snapshot_map.get(symbol) or snapshot_map.get(f"{symbol}.NS")
            if current_price is None or current_price <= 0:
                continue

            # Check Target High
            if w.target_high_price and float(w.target_high_price) > 0:
                target_high = float(w.target_high_price)
                if current_price >= target_high:
                    if not w.is_above_high:
                        w.is_above_high = True
                        dedup = f"stock_target:{w.user_id}:{symbol}:HIGH:{int(target_high)}:{today_str}"
                        title = f"Stock Alert: {symbol} Target High Crossed"
                        msg = f"{symbol} crossed your target high price of ₹{target_high:,.2f} (Current: ₹{current_price:,.2f})."
                        n = await self.notif_svc.create_and_send_notification(
                            user_id=w.user_id,
                            title=title,
                            message=msg,
                            notification_type="STOCK_PRICE_TARGET",
                            action_url=f"/dashboard/market-analysis?symbol={symbol}",
                            send_push=True,
                            dedup_key=dedup,
                        )
                        if n:
                            dispatched += 1
                else:
                    # Re-arm High target when price drops back below target
                    if w.is_above_high:
                        w.is_above_high = False

            # Check Target Low
            if w.target_low_price and float(w.target_low_price) > 0:
                target_low = float(w.target_low_price)
                if current_price <= target_low:
                    if not w.is_below_low:
                        w.is_below_low = True
                        dedup = f"stock_target:{w.user_id}:{symbol}:LOW:{int(target_low)}:{today_str}"
                        title = f"Stock Alert: {symbol} Target Low Crossed"
                        msg = f"{symbol} dropped below your target low price of ₹{target_low:,.2f} (Current: ₹{current_price:,.2f})."
                        n = await self.notif_svc.create_and_send_notification(
                            user_id=w.user_id,
                            title=title,
                            message=msg,
                            notification_type="STOCK_PRICE_TARGET",
                            action_url=f"/dashboard/market-analysis?symbol={symbol}",
                            send_push=True,
                            dedup_key=dedup,
                        )
                        if n:
                            dispatched += 1
                else:
                    # Re-arm Low target when price rises back above target
                    if w.is_below_low:
                        w.is_below_low = False

        await self.session.commit()
        return dispatched

    # ---------------------------------------------------------------------------
    # 4. HIGH-CONFIDENCE XGBOOST ML SIGNAL ALERTS (>85% UP)
    # ---------------------------------------------------------------------------
    async def evaluate_ml_high_confidence_signals(
        self,
        prediction_svc: StockPredictionService,
    ) -> int:
        """
        Check tracked Nifty 50 stocks for >85% UP prediction signals.
        """
        stmt = select(UserStockWatchlistModel)
        watchlists = list((await self.session.execute(stmt)).scalars().all())
        if not watchlists:
            return 0

        today_str = date.today().isoformat()
        dispatched = 0

        # Unique tracked symbols
        tracked_symbols = {w.symbol.upper() for w in watchlists}

        for symbol in tracked_symbols:
            try:
                res = await prediction_svc.predict_stock_movement(symbol)
                pred = res.get("prediction", {})
                company_name = res.get("company_name", symbol)
                signal = pred.get("signal", "")
                direction = pred.get("predicted_direction", "")
                confidence = float(pred.get("confidence_percent", 0.0))

                if (signal == "BULLISH" or direction == "UP") and confidence > 85.0:
                    # Find all users tracking this symbol
                    user_watchlists = [w for w in watchlists if w.symbol.upper() == symbol]
                    for w in user_watchlists:
                        settings = await self.get_user_settings(w.user_id)
                        if not settings.ml_alerts:
                            continue

                        dedup = f"ml_signal:{w.user_id}:{symbol}:UP:{today_str}"
                        title = f"AI Market Signal: {symbol} High Confidence"
                        msg = f"XGBoost currently indicates a high-confidence UP signal for {company_name} with {confidence:.1f}% confidence."

                        n = await self.notif_svc.create_and_send_notification(
                            user_id=w.user_id,
                            title=title,
                            message=msg,
                            notification_type="ML_HIGH_CONFIDENCE_SIGNAL",
                            action_url=f"/dashboard/market-analysis?symbol={symbol}",
                            send_push=True,
                            dedup_key=dedup,
                        )
                        if n:
                            dispatched += 1
            except Exception as ml_err:
                logger.debug("[ProactiveNotif] ML prediction eval skipped for %s: %s", symbol, ml_err)

        return dispatched

    # ---------------------------------------------------------------------------
    # 5. NEWS SENTIMENT SHIFT ALERTS (HIGHLY BULLISH / BEARISH Transition)
    # ---------------------------------------------------------------------------
    async def evaluate_news_sentiment_shifts(
        self,
        prediction_svc: StockPredictionService,
    ) -> int:
        """
        Detect sentiment transitions to HIGHLY BULLISH or BEARISH for tracked companies.
        Only notifies on state TRANSITION, not repeated identical state.
        """
        stmt = select(UserStockWatchlistModel)
        watchlists = list((await self.session.execute(stmt)).scalars().all())
        if not watchlists:
            return 0

        today_str = date.today().isoformat()
        dispatched = 0

        for w in watchlists:
            settings = await self.get_user_settings(w.user_id)
            if not settings.news_alerts:
                continue

            symbol = w.symbol.upper()
            try:
                sent_res = await prediction_svc.get_stock_news_sentiment(symbol)
                curr_sentiment = (sent_res.get("sentiment_label") or "").upper()
                company_name = sent_res.get("company_name", symbol)

                # Target transition states
                is_target_state = curr_sentiment in ("HIGHLY BULLISH", "BULLISH", "BEARISH")
                prev_sentiment = (w.last_notified_sentiment or "").upper()

                if is_target_state and curr_sentiment != prev_sentiment:
                    w.last_notified_sentiment = curr_sentiment
                    dedup = f"news_shift:{w.user_id}:{symbol}:{curr_sentiment}:{today_str}"
                    title = f"News Sentiment Shift: {symbol}"
                    msg = f"News sentiment for {company_name} has shifted to {curr_sentiment.title()}."

                    n = await self.notif_svc.create_and_send_notification(
                        user_id=w.user_id,
                        title=title,
                        message=msg,
                        notification_type="NEWS_SENTIMENT_SHIFT",
                        action_url=f"/dashboard/market-analysis?symbol={symbol}",
                        send_push=True,
                        dedup_key=dedup,
                    )
                    if n:
                        dispatched += 1
            except Exception as news_err:
                logger.debug("[ProactiveNotif] News sentiment eval skipped for %s: %s", symbol, news_err)

        await self.session.commit()
        return dispatched

    # ---------------------------------------------------------------------------
    # 6. LEARNING MODULE COMPLETION NOTIFICATION
    # ---------------------------------------------------------------------------
    async def notify_learning_completion(
        self,
        user_id: int,
        course_id: str,
        course_title: str,
    ) -> Optional[int]:
        """
        Trigger LEARNING_MODULE_COMPLETED notification upon module completion.
        Idempotent per user per course.
        """
        settings = await self.get_user_settings(user_id)
        if not settings.learning_alerts:
            return None

        dedup = f"learning:{user_id}:{course_id}:completed"
        title = "Learning Module Completed 🎉"
        msg = f"Congratulations! You completed the '{course_title}' module."

        n = await self.notif_svc.create_and_send_notification(
            user_id=user_id,
            title=title,
            message=msg,
            notification_type="LEARNING_MODULE_COMPLETED",
            action_url="/dashboard/learning-hub",
            send_push=True,
            dedup_key=dedup,
        )
        return 1 if n else 0

    # ---------------------------------------------------------------------------
    # 7. WEEKLY EXPENSE LOGGING REMINDER (Sunday Evening)
    # ---------------------------------------------------------------------------
    async def evaluate_weekly_expense_reminders(self) -> int:
        """
        Sunday evening evaluation for active users who logged 0 expenses during current week.
        """
        stmt = select(UserModel).where(UserModel.account_status == "ACTIVE")
        users = list((await self.session.execute(stmt)).scalars().all())

        dispatched = 0

        for user in users:
            settings = await self.get_user_settings(user.user_id)
            if not settings.weekly_reminders:
                continue

            tz_name = settings.timezone or "Asia/Kolkata"
            try:
                user_tz = zoneinfo.ZoneInfo(tz_name)
            except Exception:
                user_tz = zoneinfo.ZoneInfo("Asia/Kolkata")

            now_user = datetime.now(user_tz)
            # Sunday is weekday 6
            if now_user.weekday() != 6:
                continue

            # Current week bounds (Monday 00:00 to Sunday 23:59)
            start_of_week = (now_user - timedelta(days=6)).date()
            end_of_week = now_user.date()
            year, week_num, _ = now_user.isocalendar()

            dedup = f"weekly_reminder:{user.user_id}:{year}-W{week_num:02d}"

            # Check expense count for week
            exp_stmt = select(func.count(ExpenseModel.expense_id)).where(
                ExpenseModel.expense_date >= start_of_week,
                ExpenseModel.expense_date <= end_of_week,
            ).where(ExpenseModel.user_id == user.user_id)

            count = (await self.session.execute(exp_stmt)).scalar() or 0

            if count == 0:
                title = "Weekly Expense Reminder"
                msg = "You haven't logged any expenses this week. Take a moment to update your expenses."
                n = await self.notif_svc.create_and_send_notification(
                    user_id=user.user_id,
                    title=title,
                    message=msg,
                    notification_type="WEEKLY_EXPENSE_REMINDER",
                    action_url="/dashboard/expense-tracker",
                    send_push=True,
                    dedup_key=dedup,
                )
                if n:
                    dispatched += 1

        return dispatched
