"""
Pydantic schemas for Financial Goals (FRD-041).
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GoalBase(BaseModel):
    goal_name: str = Field(..., min_length=1, max_length=150, description="Name of the goal")
    target_quantity: float = Field(..., gt=0, description="Target financial goal amount/units")
    unit: Optional[str] = Field(default="INR", max_length=20, description="Currency or unit (e.g. INR, Gold, Stocks)")
    start_date: Optional[date] = Field(default=None, description="Start date of the goal")
    end_date: date = Field(..., description="Target completion deadline date")
    notes: Optional[str] = Field(default=None, max_length=500, description="Optional goal notes or purpose")
    investment_type_id: Optional[int] = Field(default=None, description="Optional investment type ID")
    investment_name: Optional[str] = Field(default=None, description="Investment type name (e.g. Gold, Stocks, Mutual Funds)")


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    goal_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    target_quantity: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = Field(default=None, max_length=20)
    end_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class GoalProgressCreate(BaseModel):
    quantity_added: float = Field(..., gt=0, description="Amount/units added to goal progress")
    progress_date: Optional[date] = Field(default=None, description="Date of progress contribution")
    remarks: Optional[str] = Field(default=None, max_length=255, description="Remarks or asset notes")
    asset_type: Optional[str] = Field(default="Gold", description="Asset type used for contribution")


class GoalProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    progress_id: int
    goal_id: int
    quantity_added: float
    progress_date: date
    remarks: Optional[str] = None
    created_at: datetime


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    goal_id: int
    user_id: int
    investment_type_id: int
    status_id: int
    goal_name: str
    notes: Optional[str] = None
    target_quantity: float
    current_quantity: float
    unit: str
    start_date: date
    end_date: date
    completed_at: Optional[datetime] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    progress_pct: Optional[float] = None
    days_left: Optional[int] = None
    status: Optional[str] = None
    history: Optional[List[GoalProgressResponse]] = None


class InvestmentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investment_type_id: int
    investment_name: str
    default_unit: str
    description: Optional[str] = None
    is_active: bool
