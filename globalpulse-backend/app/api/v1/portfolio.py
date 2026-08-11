"""
FastAPI Investment Portfolio Endpoints.
Prefix: /portfolio
Protected by JWT authentication dependency (get_current_active_user).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.models.user_model import UserModel
from app.db.session import get_db_session
from app.schemas.portfolio import HoldingItem, InvestmentCreate, InvestmentUpdate, PortfolioSummaryResponse
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["Portfolio Management"])


@router.get("/summary", response_model=PortfolioSummaryResponse, status_code=status.HTTP_200_OK)
async def get_portfolio_summary(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch user portfolio summary, totals, holdings, and live stock market performance metrics."""
    service = PortfolioService(db)
    return await service.get_portfolio_summary(current_user.user_id)


@router.post("", response_model=HoldingItem, status_code=status.HTTP_201_CREATED)
async def add_investment(
    req: InvestmentCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add a new investment holding for the authenticated user."""
    service = PortfolioService(db)
    return await service.add_investment(current_user.user_id, req)


@router.put("/{investment_id}", response_model=HoldingItem, status_code=status.HTTP_200_OK)
async def update_investment(
    investment_id: int,
    req: InvestmentUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update an existing holding for the authenticated user."""
    service = PortfolioService(db)
    return await service.update_investment(current_user.user_id, investment_id, req)


@router.delete("/{investment_id}", status_code=status.HTTP_200_OK)
async def delete_investment(
    investment_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete an investment holding for the authenticated user."""
    service = PortfolioService(db)
    await service.delete_investment(current_user.user_id, investment_id)
    return {"message": "Investment holding deleted successfully."}
