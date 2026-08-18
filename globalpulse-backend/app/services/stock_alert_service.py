"""
GlobalPulse Stock Price Alert Service
Detects significant stock price movements and broadcasts push notifications
to all active users so they are immediately informed of major market events.

Thresholds:
  - Surge   : change_pct >= +3.0%  → "📈 Stock Surge Alert"
  - Drop    : change_pct <= -3.0%  → "📉 Stock Drop Alert"
  - Notable : |change_pct| >= 2.0% → "⚡ Stock Price Alert"

Deduplication: one alert per (symbol, direction_bucket, calendar_date) per user.
"""
import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification_model import NotificationModel
from app.db.models.user_model import UserModel

logger = logging.getLogger(__name__)

# Minimum absolute % move required to trigger a notification
SURGE_THRESHOLD: float = 3.0   # >= +3%  → Surge
DROP_THRESHOLD: float = -3.0   # <= -3%  → Drop
NOTABLE_THRESHOLD: float = 2.0  # |%| >= 2% → Notable


def _direction_bucket(change_pct: float) -> str:
    """Classify price move into a stable string bucket for dedup."""
    if change_pct >= SURGE_THRESHOLD:
        return "SURGE"
    if change_pct <= DROP_THRESHOLD:
        return "DROP"
    return "NOTABLE"


def _build_notification_content(
    company_name: str,
    symbol: str,
    current_price: float,
    change: float,
    change_pct: float,
) -> tuple[str, str]:
    """
    Build a clear, informative notification title + message.
    Never fabricates values — uses only the data passed in.
    """
    arrow = "📈" if change_pct >= 0 else "📉"
    pct_str = f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%"
    chg_str = f"{'+' if change > 0 else ''}{change:.2f}"
    price_str = f"₹{current_price:,.2f}"

    if change_pct >= SURGE_THRESHOLD:
        title = f"📈 Stock Surge: {symbol}"
        message = (
            f"{company_name} surged {pct_str} to {price_str} "
            f"(change: {chg_str}). Strong bullish momentum detected today."
        )
    elif change_pct <= DROP_THRESHOLD:
        title = f"📉 Stock Drop: {symbol}"
        message = (
            f"{company_name} dropped {pct_str} to {price_str} "
            f"(change: {chg_str}). Significant selling pressure observed today."
        )
    else:
        title = f"⚡ Price Move: {symbol}"
        message = (
            f"{company_name} moved {pct_str} to {price_str} "
            f"(change: {chg_str}). Notable price movement today."
        )

    return title, message


async def _has_duplicate_stock_alert(
    session: AsyncSession,
    user_id: int,
    symbol: str,
    direction_bucket: str,
    today: date,
) -> bool:
    """
    Return True if an identical stock alert for this user/symbol/direction/date already exists.
    Prevents flooding the same notification multiple times per day per stock.
    """
    identifier_fragment = f"[{symbol}:{direction_bucket}:{today.isoformat()}]"
    stmt = (
        select(func.count())
        .select_from(NotificationModel)
        .where(
            NotificationModel.user_id == user_id,
            NotificationModel.notification_type == "MARKET_ALERT",
            NotificationModel.message.contains(identifier_fragment),
        )
    )
    res = await session.execute(stmt)
    return (res.scalar_one() or 0) > 0


async def _get_all_active_user_ids(session: AsyncSession) -> List[int]:
    """Fetch all ACTIVE users' IDs from the database."""
    stmt = select(UserModel.user_id).where(UserModel.account_status == "ACTIVE")
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def broadcast_stock_price_alerts(
    session: AsyncSession,
    snapshot_items: List[Dict],
) -> None:
    """
    After each market snapshot fetch, evaluate each stock's daily price move.
    If a significant move is detected, send a notification to ALL active users.

    This is intentionally a fire-and-continue routine — any failure on a single
    stock or user does not block others.

    Args:
        session: AsyncSession with a live DB connection.
        snapshot_items: List of snapshot dicts from _execute_snapshot_fetch.
    """
    if not snapshot_items:
        return

    today = date.today()

    # Identify stocks with significant moves
    significant: List[Dict] = []
    for item in snapshot_items:
        change_pct = item.get("change_percent", 0.0)
        if change_pct is None:
            continue
        if abs(change_pct) >= NOTABLE_THRESHOLD:
            significant.append(item)

    if not significant:
        logger.debug("[StockAlert] No significant price moves detected (threshold: ±%.1f%%)", NOTABLE_THRESHOLD)
        return

    logger.info(
        "[StockAlert] %d stocks crossed price alert threshold — fetching active user list",
        len(significant),
    )

    # Fetch all active users once
    try:
        user_ids = await _get_all_active_user_ids(session)
    except Exception as e:
        logger.warning("[StockAlert] Failed to fetch active user IDs: %s", e)
        return

    if not user_ids:
        logger.debug("[StockAlert] No active users found — skipping notifications")
        return

    sent_count = 0
    skipped_count = 0

    for item in significant:
        symbol = item.get("symbol", "")
        company_name = item.get("company_name", symbol)
        current_price = item.get("current_price", 0.0)
        change = item.get("change", 0.0)
        change_pct = item.get("change_percent", 0.0)

        if not symbol or current_price <= 0:
            continue

        direction_bucket = _direction_bucket(change_pct)
        title, base_message = _build_notification_content(
            company_name, symbol, current_price, change, change_pct
        )
        # Embed dedup token inside message so _has_duplicate can detect it
        dedup_token = f" [{symbol}:{direction_bucket}:{today.isoformat()}]"
        message = base_message + dedup_token

        for user_id in user_ids:
            try:
                # Skip if already sent today
                already_sent = await _has_duplicate_stock_alert(
                    session, user_id, symbol, direction_bucket, today
                )
                if already_sent:
                    skipped_count += 1
                    continue

                notification = NotificationModel(
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type="MARKET_ALERT",
                    is_read=False,
                    action_url=f"/dashboard/stocks/{symbol}",
                )
                session.add(notification)
                sent_count += 1

            except Exception as e:
                logger.warning(
                    "[StockAlert] Failed to queue notification for user %d / %s: %s",
                    user_id, symbol, e,
                )

    # Commit all queued notifications in one transaction
    try:
        if sent_count > 0:
            await session.commit()
            logger.info(
                "[StockAlert] Dispatched %d stock price notifications (%d skipped as duplicates)",
                sent_count,
                skipped_count,
            )
    except Exception as commit_err:
        logger.error("[StockAlert] Failed to commit stock alert notifications: %s", commit_err)
        await session.rollback()
