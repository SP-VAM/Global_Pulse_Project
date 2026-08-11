"""
Service Layer for User Investment Portfolio.
Fetches live market quotes, performs dynamic portfolio math, and enforces user isolation.
"""
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.portfolio_model import UserInvestmentModel
from app.db.models.user_model import AuditLogModel
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.portfolio import HoldingItem, InvestmentCreate, InvestmentUpdate, PortfolioSummaryResponse
from app.providers.stock_provider_factory import get_stock_provider

logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.portfolio_repo = PortfolioRepository(session)
        self.stock_provider = get_stock_provider()

    async def _audit(self, user_id: int, action: str, description: str, record_id: Optional[int] = None) -> None:
        """Create audit log entry."""
        try:
            log_entry = AuditLogModel(
                user_id=user_id,
                module_name="PORTFOLIO",
                table_name="user_investments",
                record_id=record_id,
                action=action,
                description=description,
            )
            self.session.add(log_entry)
            await self.session.commit()
        except Exception as exc:
            logger.warning("[Portfolio Audit Warning] %s", exc)

    async def get_portfolio_summary(self, user_id: int) -> PortfolioSummaryResponse:
        """Fetch all user holdings, fetch live market prices, and compute portfolio summary."""
        investments = await self.portfolio_repo.get_user_investments(user_id)
        if not investments:
            return PortfolioSummaryResponse(
                portfolio_value=0.0,
                invested_amount=0.0,
                total_profit_loss=0.0,
                percentage_return=0.0,
                todays_change=0.0,
                total_holdings_count=0,
                holdings=[],
            )

        holdings_list: List[HoldingItem] = []
        total_portfolio_value = 0.0
        total_invested_amount = 0.0
        total_todays_change = 0.0

        for inv in investments:
            qty = float(inv.quantity)
            buy_price = float(inv.purchase_price)
            invested_val = qty * buy_price

            # Fetch current quote from market provider
            current_price = buy_price
            todays_change_per_share = 0.0
            todays_change_pct = 0.0
            sparkline = [buy_price * 0.98, buy_price * 0.99, buy_price * 1.01, buy_price * 1.02]

            try:
                quote = await self.stock_provider.get_quote(inv.ticker)
                if quote and quote.current_price and quote.current_price > 0:
                    current_price = float(quote.current_price)
                    if quote.change:
                        todays_change_per_share = float(quote.change)
                    if quote.percent_change:
                        todays_change_pct = float(quote.percent_change)
                    sparkline = [
                        current_price * 0.97,
                        current_price * 0.98,
                        current_price * 0.99,
                        current_price * 1.00,
                        current_price,
                    ]
            except Exception as exc:
                logger.warning("[Portfolio Quote Error] Ticker %s: %s", inv.ticker, exc)

            current_val = qty * current_price
            gain_loss = current_val - invested_val
            pct_return = (gain_loss / invested_val * 100.0) if invested_val > 0 else 0.0
            todays_gain_loss = qty * todays_change_per_share

            total_portfolio_value += current_val
            total_invested_amount += invested_val
            total_todays_change += todays_gain_loss

            item = HoldingItem(
                investment_id=inv.investment_id,
                user_id=inv.user_id,
                asset_type=inv.asset_type,
                ticker=inv.ticker,
                company_name=inv.company_name,
                quantity=qty,
                purchase_price=buy_price,
                purchase_date=inv.purchase_date,
                exchange=inv.exchange,
                broker_name=inv.broker_name,
                investment_source=inv.investment_source,
                notes=inv.notes,
                created_at=inv.created_at,
                current_price=round(current_price, 2),
                invested_value=round(invested_val, 2),
                current_value=round(current_val, 2),
                total_gain_loss=round(gain_loss, 2),
                percentage_return=round(pct_return, 2),
                todays_change=round(todays_gain_loss, 2),
                todays_change_pct=round(todays_change_pct, 2),
                sparkline_points=[round(p, 2) for p in sparkline],
            )
            holdings_list.append(item)

        total_pl = total_portfolio_value - total_invested_amount
        total_pct_return = (total_pl / total_invested_amount * 100.0) if total_invested_amount > 0 else 0.0

        return PortfolioSummaryResponse(
            portfolio_value=round(total_portfolio_value, 2),
            invested_amount=round(total_invested_amount, 2),
            total_profit_loss=round(total_pl, 2),
            percentage_return=round(total_pct_return, 2),
            todays_change=round(total_todays_change, 2),
            total_holdings_count=len(holdings_list),
            holdings=holdings_list,
        )

    async def add_investment(self, user_id: int, req: InvestmentCreate) -> HoldingItem:
        """Add a new investment holding."""
        inv = await self.portfolio_repo.create(
            {
                "user_id": user_id,
                "asset_type": req.asset_type.upper() if req.asset_type else "STOCKS",
                "ticker": req.ticker.upper().strip(),
                "company_name": req.company_name.strip(),
                "quantity": req.quantity,
                "purchase_price": req.purchase_price,
                "purchase_date": req.purchase_date,
                "exchange": req.exchange or "NSE",
                "broker_name": req.broker_name,
                "notes": req.notes,
            }
        )

        await self._audit(user_id, "INVESTMENT_CREATED", f"Added {inv.quantity} shares of {inv.ticker}", inv.investment_id)
        summary = await self.get_portfolio_summary(user_id)
        match = next((h for h in summary.holdings if h.investment_id == inv.investment_id), None)
        if match:
            return match
        return HoldingItem(
            investment_id=inv.investment_id,
            user_id=user_id,
            asset_type=inv.asset_type,
            ticker=inv.ticker,
            company_name=inv.company_name,
            quantity=float(inv.quantity),
            purchase_price=float(inv.purchase_price),
            purchase_date=inv.purchase_date,
            exchange=inv.exchange,
            broker_name=inv.broker_name,
            investment_source=inv.investment_source,
            notes=inv.notes,
            created_at=inv.created_at,
            current_price=float(inv.purchase_price),
            invested_value=float(inv.quantity * inv.purchase_price),
            current_value=float(inv.quantity * inv.purchase_price),
            total_gain_loss=0.0,
            percentage_return=0.0,
            todays_change=0.0,
            todays_change_pct=0.0,
            sparkline_points=[],
        )

    async def update_investment(self, user_id: int, investment_id: int, req: InvestmentUpdate) -> HoldingItem:
        """Update an existing holding verified by user_id."""
        inv = await self.portfolio_repo.get_user_investment_by_id(user_id, investment_id)
        if not inv:
            raise ValidationError("Investment holding not found.")

        updates = req.model_dump(exclude_unset=True)
        if "ticker" in updates and updates["ticker"]:
            updates["ticker"] = updates["ticker"].upper().strip()
        if "asset_type" in updates and updates["asset_type"]:
            updates["asset_type"] = updates["asset_type"].upper()

        updated = await self.portfolio_repo.update(investment_id, updates)
        await self._audit(user_id, "INVESTMENT_UPDATED", f"Updated holding {updated.ticker}", investment_id)

        summary = await self.get_portfolio_summary(user_id)
        match = next((h for h in summary.holdings if h.investment_id == investment_id), None)
        if match:
            return match
        raise ValidationError("Holding updated successfully.")

    async def delete_investment(self, user_id: int, investment_id: int) -> bool:
        """Delete an investment holding verified by user_id."""
        inv = await self.portfolio_repo.get_user_investment_by_id(user_id, investment_id)
        if not inv:
            raise ValidationError("Investment holding not found.")

        ticker = inv.ticker
        deleted = await self.portfolio_repo.delete(investment_id)
        await self._audit(user_id, "INVESTMENT_DELETED", f"Deleted holding {ticker}", investment_id)
        return deleted
