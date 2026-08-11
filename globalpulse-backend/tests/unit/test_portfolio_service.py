import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.schemas.portfolio import InvestmentCreate, InvestmentUpdate
from app.services.portfolio_service import PortfolioService
from app.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_portfolio_empty_summary():
    mock_session = AsyncMock()
    service = PortfolioService(mock_session)
    service.portfolio_repo.get_user_investments = AsyncMock(return_value=[])

    summary = await service.get_portfolio_summary(10)
    assert summary.portfolio_value == 0.0
    assert summary.invested_amount == 0.0
    assert summary.total_holdings_count == 0
    assert len(summary.holdings) == 0


@pytest.mark.asyncio
async def test_portfolio_crud_and_calculation():
    mock_session = AsyncMock()
    service = PortfolioService(mock_session)

    # Mock stock quote
    mock_quote = MagicMock(current_price=2500.0, change=50.0, percent_change=2.0)
    service.stock_provider.get_quote = AsyncMock(return_value=mock_quote)

    # Mock holding item in DB
    mock_inv = MagicMock(
        investment_id=1,
        user_id=10,
        asset_type="STOCKS",
        ticker="RELIANCE.NS",
        company_name="Reliance Industries",
        quantity=10.0,
        purchase_price=2000.0,
        purchase_date=date(2026, 8, 1),
        exchange="NSE",
        broker_name="Zerodha",
        investment_source="MANUAL",
        notes="Long term",
        created_at=date(2026, 8, 1),
    )

    service.portfolio_repo.get_user_investments = AsyncMock(return_value=[mock_inv])
    service.portfolio_repo.get_user_investment_by_id = AsyncMock(return_value=mock_inv)
    service.portfolio_repo.create = AsyncMock(return_value=mock_inv)
    service.portfolio_repo.update = AsyncMock(return_value=mock_inv)
    service.portfolio_repo.delete = AsyncMock(return_value=True)

    summary = await service.get_portfolio_summary(10)
    assert summary.invested_amount == 20000.0  # 10 * 2000
    assert summary.portfolio_value == 25000.0   # 10 * 2500
    assert summary.total_profit_loss == 5000.0
    assert summary.percentage_return == 25.0

    # Add Investment
    new_inv = await service.add_investment(
        10,
        InvestmentCreate(
            ticker="RELIANCE.NS",
            company_name="Reliance Industries",
            quantity=10.0,
            purchase_price=2000.0,
            purchase_date=date(2026, 8, 1),
        ),
    )
    assert new_inv.investment_id == 1

    # Delete Investment
    deleted = await service.delete_investment(10, 1)
    assert deleted is True
