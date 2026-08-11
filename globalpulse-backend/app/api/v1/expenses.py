"""
FastAPI Expense Tracker Endpoints.
Prefix: /expenses
Protected by JWT authentication dependency (get_current_active_user).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.models.user_model import UserModel
from app.db.session import get_db_session
from app.schemas.expense import (
    BudgetCreate,
    BudgetResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSummaryResponse,
    ExpenseUpdate,
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
)
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expense Tracker"])


@router.get("/summary", response_model=ExpenseSummaryResponse, status_code=status.HTTP_200_OK)
async def get_monthly_summary(
    year: Optional[int] = Query(None, description="Year e.g. 2026"),
    month: Optional[int] = Query(None, description="Month (1-12)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch monthly expense summary, incomes, expenses, categories, and budgets for active user."""
    now = datetime.now()
    target_year = year or now.year
    target_month = month or now.month

    service = ExpenseService(db)
    return await service.get_monthly_summary(current_user.user_id, target_year, target_month)


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    req: ExpenseCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Record a new expense for the authenticated user."""
    service = ExpenseService(db)
    return await service.create_expense(current_user.user_id, req)


@router.put("/{expense_id}", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
async def update_expense(
    expense_id: int,
    req: ExpenseUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update an expense record for the authenticated user."""
    service = ExpenseService(db)
    return await service.update_expense(current_user.user_id, expense_id, req)


@router.delete("/{expense_id}", status_code=status.HTTP_200_OK)
async def delete_expense(
    expense_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete an expense record for the authenticated user."""
    service = ExpenseService(db)
    await service.delete_expense(current_user.user_id, expense_id)
    return {"message": "Expense record deleted successfully."}


@router.post("/income", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
async def create_income(
    req: IncomeCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Record a new income entry for the authenticated user."""
    service = ExpenseService(db)
    return await service.create_income(current_user.user_id, req)


@router.put("/income/{income_id}", response_model=IncomeResponse, status_code=status.HTTP_200_OK)
async def update_income(
    income_id: int,
    req: IncomeUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update an income record for the authenticated user."""
    service = ExpenseService(db)
    return await service.update_income(current_user.user_id, income_id, req)


@router.delete("/income/{income_id}", status_code=status.HTTP_200_OK)
async def delete_income(
    income_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete an income entry for the authenticated user."""
    service = ExpenseService(db)
    await service.delete_income(current_user.user_id, income_id)
    return {"message": "Income record deleted successfully."}


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_200_OK)
async def save_budget(
    req: BudgetCreate,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create or update category budget allocation."""
    service = ExpenseService(db)
    return await service.save_budget(current_user.user_id, req)


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_200_OK)
async def delete_budget(
    budget_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a budget record for the authenticated user."""
    service = ExpenseService(db)
    await service.delete_budget(current_user.user_id, budget_id)
    return {"message": "Budget record deleted successfully."}

