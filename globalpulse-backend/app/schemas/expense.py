"""
Pydantic Schemas for Expense Tracker (Categories, Expenses, Incomes, Budgets).
Serializes fields to camelCase for frontend compatibility.
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class ExpenseCategoryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    category_id: int
    category_name: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    is_active: bool


def validate_max_13_digits(v: Optional[float]) -> Optional[float]:
    if v is not None:
        int_part = str(int(abs(v)))
        if len(int_part) > 13 or abs(v) >= 1e13:
            raise ValueError("Amount cannot exceed 13 digits.")
    return v


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    category_id: Optional[int] = Field(None)
    category_name: Optional[str] = Field(None)
    amount: float = Field(..., gt=0, lt=1e13)
    expense_date: date
    payment_method: Optional[str] = Field("UPI")
    notes: Optional[str] = Field(None)

    @field_validator("amount")
    @classmethod
    def check_amount_digits(cls, v: float) -> float:
        return validate_max_13_digits(v)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    expense_id: int
    user_id: int
    category_id: int
    amount: float
    expense_date: date
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    category: Optional[ExpenseCategoryResponse] = None


class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    category_id: Optional[int] = Field(None)
    category_name: Optional[str] = Field(None)
    amount: Optional[float] = Field(None, gt=0, lt=1e13)
    expense_date: Optional[date] = Field(None)
    payment_method: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)

    @field_validator("amount")
    @classmethod
    def check_amount_digits(cls, v: Optional[float]) -> Optional[float]:
        return validate_max_13_digits(v)


class IncomeCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    amount: float = Field(..., gt=0, lt=1e13)
    income_date: date
    payment_method: Optional[str] = Field("Salary")
    notes: Optional[str] = Field(None)

    @field_validator("amount")
    @classmethod
    def check_amount_digits(cls, v: float) -> float:
        return validate_max_13_digits(v)


class IncomeUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    amount: Optional[float] = Field(None, gt=0, lt=1e13)
    income_date: Optional[date] = Field(None)
    payment_method: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)

    @field_validator("amount")
    @classmethod
    def check_amount_digits(cls, v: Optional[float]) -> Optional[float]:
        return validate_max_13_digits(v)


class IncomeResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    income_id: int
    user_id: int
    amount: float
    income_date: date
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class BudgetCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    category_id: Optional[int] = Field(None)
    category_name: Optional[str] = Field(None)
    budget_amount: float = Field(..., gt=0)
    budget_month: int = Field(..., ge=1, le=12)
    budget_year: int = Field(..., ge=2000, le=2100)


class BudgetUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    budget_amount: Optional[float] = Field(None, gt=0)
    budget_month: Optional[int] = Field(None, ge=1, le=12)
    budget_year: Optional[int] = Field(None, ge=2000, le=2100)



class BudgetResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    budget_id: int
    user_id: int
    category_id: int
    budget_amount: float
    budget_month: int
    budget_year: int
    category: Optional[ExpenseCategoryResponse] = None


class CategoryBreakdownItem(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    label: str
    amount: float
    color: str


class ExpenseSummaryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    year: int
    month: int
    monthly_spending: float
    monthly_income: float
    savings: float
    expenses: List[ExpenseResponse]
    incomes: List[IncomeResponse]
    budgets: List[BudgetResponse]
    categories: List[ExpenseCategoryResponse]
