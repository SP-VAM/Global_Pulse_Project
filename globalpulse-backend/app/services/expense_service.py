"""
Expense Tracker Service.
Business logic for managing user expenses, incomes, budgets, and monthly totals.
"""
import logging
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.db.models.expense_model import BudgetModel, ExpenseCategoryModel, ExpenseModel, IncomeModel
from app.repositories.expense_repository import BudgetRepository, ExpenseRepository, IncomeRepository
from app.schemas.expense import (
    BUDGET_APPROACHING_THRESHOLD,
    BudgetAlertItem,
    BudgetCreate,
    BudgetResponse,
    ExpenseCategoryResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseSummaryResponse,
    IncomeCreate,
    IncomeResponse,
    TransactionFilterParams,
    TransactionItem,
    TransactionListResponse,
)


logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    {"category_name": "Rent", "icon_name": "Home", "color_code": "#3b82f6"},
    {"category_name": "Shopping", "icon_name": "ShoppingBag", "color_code": "#8b5cf6"},
    {"category_name": "Food", "icon_name": "Utensils", "color_code": "#06b6d4"},
    {"category_name": "Transport", "icon_name": "Car", "color_code": "#10b981"},
    {"category_name": "Entertainment", "icon_name": "Film", "color_code": "#f59e0b"},
    {"category_name": "Health", "icon_name": "HeartPulse", "color_code": "#ef4444"},
    {"category_name": "Bills", "icon_name": "Receipt", "color_code": "#64748b"},
]


# In-memory cached default categories to avoid repeated DB hits for static metadata
_CACHED_CATEGORIES: Optional[List[ExpenseCategoryModel]] = None


class ExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expense_repo = ExpenseRepository(session)
        self.income_repo = IncomeRepository(session)
        self.budget_repo = BudgetRepository(session)

    async def ensure_default_categories(self) -> List[ExpenseCategoryModel]:
        """Ensure standard default expense categories exist in database and cache them in memory."""
        global _CACHED_CATEGORIES
        if _CACHED_CATEGORIES:
            return _CACHED_CATEGORIES

        stmt = select(ExpenseCategoryModel).where(ExpenseCategoryModel.is_active == True)
        res = await self.session.execute(stmt)
        existing = list(res.scalars().all())

        if not existing:
            for cat_data in DEFAULT_CATEGORIES:
                cat = ExpenseCategoryModel(**cat_data)
                self.session.add(cat)
            await self.session.commit()

            res = await self.session.execute(stmt)
            existing = list(res.scalars().all())

        _CACHED_CATEGORIES = existing
        return existing

    async def get_or_create_category_by_name(self, category_name: str) -> ExpenseCategoryModel:
        """Find or create category by name."""
        stmt = select(ExpenseCategoryModel).where(func.lower(ExpenseCategoryModel.category_name) == category_name.lower())
        res = await self.session.execute(stmt)
        cat = res.scalar_one_or_none()
        if not cat:
            cat = ExpenseCategoryModel(category_name=category_name.capitalize(), color_code="#64748b")
            self.session.add(cat)
            await self.session.commit()
            await self.session.refresh(cat)
            # Invalidate category cache so new custom categories are included
            global _CACHED_CATEGORIES
            _CACHED_CATEGORIES = None
        return cat

    async def get_monthly_summary(self, user_id: int, year: int, month: int) -> ExpenseSummaryResponse:
        """Fetch complete monthly financial summary for user, including budget alerts."""
        categories = await self.ensure_default_categories()

        # Query user month records in minimal round-trips
        expenses = await self.expense_repo.get_user_expenses_by_month(user_id, year, month)
        incomes = await self.income_repo.get_user_incomes_by_month(user_id, year, month)
        budgets = await self.budget_repo.get_user_budgets_by_month(user_id, year, month)

        # Accurately derive monthly totals directly from the fetched month records (eliminating redundant DB round-trips)
        spending = sum(float(exp.amount) for exp in expenses)
        income = sum(float(inc.amount) for inc in incomes)

        # ----------------------------------------------------------------
        # FRD-017: Compute per-category spending to generate budget alerts.
        # Only expenses for the requested year/month contribute.
        # ----------------------------------------------------------------
        spending_by_category: dict[int, float] = {}
        for exp in expenses:
            cat_id = exp.category_id
            spending_by_category[cat_id] = spending_by_category.get(cat_id, 0.0) + float(exp.amount)

        budget_alerts: List[BudgetAlertItem] = []
        for budget in budgets:
            cat_spent = spending_by_category.get(budget.category_id, 0.0)
            limit = float(budget.budget_amount)
            if limit <= 0:
                continue
            utilization = cat_spent / limit  # 0.0 → unbounded
            utilization_pct = round(utilization * 100, 1)

            cat_name = (
                budget.category.category_name
                if budget.category
                else f"Category {budget.category_id}"
            )

            if cat_spent > limit:
                # Exceeded: spending has crossed the budget limit
                budget_alerts.append(
                    BudgetAlertItem(
                        category_id=budget.category_id,
                        category_name=cat_name,
                        alert_type="exceeded",
                        spent=cat_spent,
                        limit=limit,
                        utilization_pct=utilization_pct,
                    )
                )
            elif utilization >= BUDGET_APPROACHING_THRESHOLD:
                # Approaching: at or above 80% but not yet exceeded
                budget_alerts.append(
                    BudgetAlertItem(
                        category_id=budget.category_id,
                        category_name=cat_name,
                        alert_type="approaching",
                        spent=cat_spent,
                        limit=limit,
                        utilization_pct=utilization_pct,
                    )
                )

        return ExpenseSummaryResponse(
            year=year,
            month=month,
            monthly_spending=float(spending),
            monthly_income=float(income),
            savings=float(income - spending),
            expenses=[ExpenseResponse.model_validate(e) for e in expenses],
            incomes=[IncomeResponse.model_validate(i) for i in incomes],
            budgets=[BudgetResponse.model_validate(b) for b in budgets],
            categories=[ExpenseCategoryResponse.model_validate(c) for c in categories],
            budget_alerts=budget_alerts,
        )


    async def create_expense(self, user_id: int, req: ExpenseCreate) -> ExpenseResponse:
        """Record a new expense for the user."""
        cat_id = req.category_id
        if not cat_id and req.category_name:
            cat = await self.get_or_create_category_by_name(req.category_name)
            cat_id = cat.category_id
        elif not cat_id:
            categories = await self.ensure_default_categories()
            cat_id = categories[0].category_id

        pm = req.payment_method.strip().upper().replace(" ", "_") if req.payment_method else "OTHER"
        expense = await self.expense_repo.create(
            {
                "user_id": user_id,
                "category_id": cat_id,
                "amount": req.amount,
                "expense_date": req.expense_date,
                "payment_method": pm,
                "notes": req.notes,
            }
        )

        # 1. Trigger successful expense transaction notification
        cat_name = req.category_name or "Expense"
        try:
            from app.services.notification_service import NotificationService
            cat_stmt = select(ExpenseCategoryModel).where(ExpenseCategoryModel.category_id == cat_id)
            cat_res = await self.session.execute(cat_stmt)
            cat_obj = cat_res.scalar_one_or_none()
            if cat_obj:
                cat_name = cat_obj.category_name

            notif_svc = NotificationService(self.session)
            await notif_svc.create_and_send_notification(
                user_id=user_id,
                title="Expense Added Successfully",
                message=f"Your expense of ₹{float(req.amount):,.2f} for {cat_name} was added successfully.",
                notification_type="FINANCIAL",
                action_url="/dashboard/expenses",
                send_push=True,
            )
        except Exception as exp_notif_err:
            logger.debug("Expense transaction notification skipped: %s", exp_notif_err)

        # 2. Trigger unusual account activity notification if transaction is anomalously large
        try:
            exp_date = req.expense_date or date.today()
            month_exps = await self.expense_repo.get_user_expenses_by_month(user_id, exp_date.year, exp_date.month)
            if len(month_exps) > 1:
                prior_exps = [float(e.amount) for e in month_exps if e.expense_id != expense.expense_id]
                avg_spent = sum(prior_exps) / len(prior_exps) if prior_exps else 0.0
                is_unusual = (avg_spent > 0 and float(req.amount) >= 3 * avg_spent and float(req.amount) >= 5000.0) or (float(req.amount) >= 100000.0)
            else:
                is_unusual = float(req.amount) >= 100000.0

            if is_unusual:
                from app.services.notification_service import NotificationService
                notif_svc = NotificationService(self.session)
                await notif_svc.create_and_send_notification(
                    user_id=user_id,
                    title="Unusual Account Activity",
                    message=f"An unusually large expense of ₹{float(req.amount):,.2f} was recorded in {cat_name}. Please review your recent activity.",
                    notification_type="SECURITY",
                    action_url="/dashboard/expenses",
                    send_push=True,
                )
        except Exception as unusual_notif_err:
            logger.debug("Unusual activity notification skipped: %s", unusual_notif_err)

        # 3. Trigger budget alert notification if month budget is exceeded
        try:
            exp_date = req.expense_date or date.today()
            budgets = await self.budget_repo.get_user_budgets_by_month(user_id, exp_date.year, exp_date.month)
            matching_budget = next((b for b in budgets if b.category_id == cat_id), None)
            if matching_budget and float(matching_budget.budget_amount) > 0:
                month_exps = await self.expense_repo.get_user_expenses_by_month(user_id, exp_date.year, exp_date.month)
                total_spent = sum(float(e.amount) for e in month_exps if e.category_id == cat_id)
                budget_limit = float(matching_budget.budget_amount)
                if total_spent >= budget_limit:
                    from app.services.notification_service import NotificationService
                    notif_svc = NotificationService(self.session)
                    await notif_svc.create_and_send_notification(
                        user_id=user_id,
                        title="Budget Alert: Limit Reached",
                        message=f"You have spent ₹{total_spent:,.2f} exceeding your monthly budget limit of ₹{budget_limit:,.2f}.",
                        notification_type="BUDGET_ALERT",
                        action_url="/dashboard/expenses",
                        send_push=True,
                    )
        except Exception as budget_notif_err:
            logger.debug("Budget notification trigger skipped: %s", budget_notif_err)

        return ExpenseResponse.model_validate(expense)

    async def create_income(self, user_id: int, req: IncomeCreate) -> IncomeResponse:
        """Record a new income entry for the user and trigger transaction notification."""
        pm = req.payment_method.strip().upper().replace(" ", "_") if req.payment_method else "OTHER"
        income = await self.income_repo.create(
            {
                "user_id": user_id,
                "amount": req.amount,
                "income_date": req.income_date,
                "payment_method": pm,
                "notes": req.notes,
            }
        )

        # Trigger successful income transaction notification
        try:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.session)
            await notif_svc.create_and_send_notification(
                user_id=user_id,
                title="Income Added Successfully",
                message=f"Your income of ₹{float(req.amount):,.2f} was added successfully.",
                notification_type="FINANCIAL",
                action_url="/dashboard/expenses",
                send_push=True,
            )
        except Exception as inc_notif_err:
            logger.debug("Income transaction notification skipped: %s", inc_notif_err)

        return IncomeResponse.model_validate(income)

    async def update_expense(self, user_id: int, expense_id: int, req: ExpenseUpdate) -> ExpenseResponse:
        """Update an existing expense belonging to user."""
        expense = await self.expense_repo.get_by_id(expense_id)
        if not expense or expense.user_id != user_id:
            raise ValidationError("Expense record not found.")

        updates = req.model_dump(exclude_unset=True)
        if "category_name" in updates:
            cat_name = updates.pop("category_name")
            if cat_name:
                cat = await self.get_or_create_category_by_name(cat_name)
                updates["category_id"] = cat.category_id

        updated = await self.expense_repo.update(expense_id, updates)
        return ExpenseResponse.model_validate(updated)

    async def delete_expense(self, user_id: int, expense_id: int) -> bool:
        """Delete an expense belonging to the user."""
        expense = await self.expense_repo.get_by_id(expense_id)
        if not expense or expense.user_id != user_id:
            raise ValidationError("Expense record not found.")
        return await self.expense_repo.delete(expense_id)

    async def update_income(self, user_id: int, income_id: int, req: IncomeUpdate) -> IncomeResponse:
        """Update an existing income belonging to user."""
        income = await self.income_repo.get_by_id(income_id)
        if not income or income.user_id != user_id:
            raise ValidationError("Income record not found.")
    
        updates = req.model_dump(exclude_unset=True)
        updated = await self.income_repo.update(income_id, updates)
        return IncomeResponse.model_validate(updated)

    async def delete_income(self, user_id: int, income_id: int) -> bool:
        """Delete an income entry belonging to user."""
        income = await self.income_repo.get_by_id(income_id)
        if not income or income.user_id != user_id:
            raise ValidationError("Income record not found.")
        return await self.income_repo.delete(income_id)

    async def save_budget(self, user_id: int, req: BudgetCreate) -> BudgetResponse:
        """Create or update a category budget for user."""
        cat_id = req.category_id
        if not cat_id and req.category_name:
            cat = await self.get_or_create_category_by_name(req.category_name)
            cat_id = cat.category_id
        elif not cat_id:
            categories = await self.ensure_default_categories()
            cat_id = categories[0].category_id

        stmt = select(BudgetModel).where(
            BudgetModel.user_id == user_id,
            BudgetModel.category_id == cat_id,
            BudgetModel.budget_year == req.budget_year,
            BudgetModel.budget_month == req.budget_month,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            updated = await self.budget_repo.update(existing.budget_id, {"budget_amount": req.budget_amount})
            return BudgetResponse.model_validate(updated)
        else:
            budget = await self.budget_repo.create(
                {
                    "user_id": user_id,
                    "category_id": cat_id,
                    "budget_amount": req.budget_amount,
                    "budget_month": req.budget_month,
                    "budget_year": req.budget_year,
                }
            )
            return BudgetResponse.model_validate(budget)

    async def delete_budget(self, user_id: int, budget_id: int) -> bool:
        """Delete a budget record belonging to user."""
        budget = await self.budget_repo.get_by_id(budget_id)
        if not budget or budget.user_id != user_id:
            raise ValidationError("Budget record not found.")
        return await self.budget_repo.delete(budget_id)

    async def get_filtered_transactions(
        self, user_id: int, params: TransactionFilterParams
    ) -> TransactionListResponse:
        """
        FRD-022: Return a filtered, merged list of expense and income transactions.

        ALL queries are restricted to the authenticated user_id.
        All filters are applied at the database level.
        Combined multi-filter: all active criteria must match simultaneously (AND logic).

        Returns a TransactionListResponse with total count and items sorted by date desc.
        """
        items: list[TransactionItem] = []

        include_expenses = params.transaction_type in (None, "expense")
        include_incomes = (
            params.transaction_type == "income"
            or (params.transaction_type is None and params.category_id is None)
        )

        if include_expenses:
            expenses = await self.expense_repo.filter_expenses(
                user_id=user_id,
                year=params.year,
                month=params.month,
                keyword=params.keyword,
                category_id=params.category_id,
                date_from=params.date_from,
                date_to=params.date_to,
                amount_min=params.amount_min,
                amount_max=params.amount_max,
            )
            for exp in expenses:
                cat_name = (
                    exp.category.category_name if exp.category else "Other"
                )
                items.append(
                    TransactionItem(
                        id=f"exp_{exp.expense_id}",
                        raw_id=exp.expense_id,
                        transaction_type="expense",
                        amount=float(exp.amount),
                        transaction_date=exp.expense_date,
                        payment_method=exp.payment_method,
                        notes=exp.notes,
                        created_at=exp.created_at,
                        category_id=exp.category_id,
                        category_name=cat_name,
                    )
                )

        if include_incomes:
            incomes = await self.income_repo.filter_incomes(
                user_id=user_id,
                year=params.year,
                month=params.month,
                keyword=params.keyword,
                date_from=params.date_from,
                date_to=params.date_to,
                amount_min=params.amount_min,
                amount_max=params.amount_max,
            )
            for inc in incomes:
                items.append(
                    TransactionItem(
                        id=f"inc_{inc.income_id}",
                        raw_id=inc.income_id,
                        transaction_type="income",
                        amount=float(inc.amount),
                        transaction_date=inc.income_date,
                        payment_method=inc.payment_method,
                        notes=inc.notes,
                        created_at=inc.created_at,
                        category_id=None,
                        category_name="Income",
                    )
                )

        # Sort merged list by date descending
        items.sort(key=lambda t: t.transaction_date, reverse=True)

        return TransactionListResponse(total=len(items), items=items)
