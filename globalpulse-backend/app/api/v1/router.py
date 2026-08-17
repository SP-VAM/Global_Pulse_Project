"""
GlobalPulse v1 API Router
Aggregates all v1 endpoint routers under the /api/v1 prefix.
"""
from fastapi import APIRouter

from app.api.v1 import (
    # Phase 1A–1C
    health,
    instruments,
    market_status,
    markets,
    quotes,
    # Phase 1D — Economic & Macro Data
    bonds,
    commodities,
    economic_events,
    forex,
    # Phase 1E — News & Global Events
    global_events,
    news,
    # Dashboard
    dashboard,
    # Phase 2 — Anomaly Engine & Correlations
    anomalies,
    # Phase 3C — India Impact Engine
    india_impact,
    # Phase 4C — Historical REST APIs & Analytics
    historical,
    # Phase 5D — AI Explanation Router
    explanation,
    # Stock ML Predictions & Technical Indicators
    stocks,
    # Authentication & User Management
    auth,
    # Expense Tracker
    expenses,
    # Investment Portfolio Management
    portfolio,
    # FRD-048 Push Notifications
    notifications,
    # FRD-041 Financial Goals & Reminders
    goals,
)

router = APIRouter(prefix="/api/v1")

# Authentication
router.include_router(auth.router)
# Push Notifications
router.include_router(notifications.router)
# Financial Goals (FRD-041)
router.include_router(goals.router)
# Expense Tracker
router.include_router(expenses.router)
# Investment Portfolio
router.include_router(portfolio.router)

# Phase 1A–1C
router.include_router(health.router)
router.include_router(markets.router)
router.include_router(instruments.router)
router.include_router(quotes.router)
router.include_router(market_status.router)

# Phase 1D — Economic & Macro Data
router.include_router(economic_events.router)
router.include_router(commodities.router)
router.include_router(forex.router)
router.include_router(bonds.router)

# Phase 1E — News & Global Events
router.include_router(news.router)
router.include_router(global_events.router)

# Dashboard
router.include_router(dashboard.router)

# Phase 2 — Anomalies, Correlations & Event Detail
router.include_router(anomalies.router)

# Phase 3C — India Impact Transmission Engine
router.include_router(india_impact.router)

# Phase 4C — Historical REST APIs & Analytics
router.include_router(historical.router)

# Phase 5D — AI Explanation & Summarization
router.include_router(explanation.router)

# Stock ML Predictions & Technical Indicators
router.include_router(stocks.router)



