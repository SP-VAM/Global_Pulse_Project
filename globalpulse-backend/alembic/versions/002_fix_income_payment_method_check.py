"""Fix incomes_payment_method_check constraint to accept application payment methods.

The old constraint only allowed: SALARY, CASH, BANK_TRANSFER, BANK TRANSFER, UPI,
DEBIT_CARD, DEBIT CARD, CREDIT_CARD, CREDIT CARD, CHEQUE, OTHER.

The application normalises frontend payment methods via:
    pm.strip().upper().replace(" ", "_")
which produces: CASH, CARD, UPI, NET_BANKING, WALLET, SALARY, OTHER.

This migration:
1. Verifies no existing income rows contain values outside the new allowed set.
2. Drops the old check constraint.
3. Creates a new check constraint with the exact set the application uses.

New allowed values (case-insensitive check):
    CASH, CARD, UPI, NET_BANKING, WALLET, SALARY, OTHER

Revision ID: 002_fix_income_payment_method_check
Revises: 001_initial_schema
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '002_fix_income_payment_method_check'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The exact set of normalized payment methods supported by the application.
# Updated when the frontend PAYMENT_METHODS list changes.
ALLOWED_PAYMENT_METHODS = ("CASH", "CARD", "UPI", "NET_BANKING", "WALLET", "SALARY", "OTHER")


def upgrade() -> None:
    bind = op.get_bind()

    # ---------------------------------------------------------------
    # SAFETY CHECK: Verify no existing income rows use values outside
    # the new allowed set.  If any are found, report them and stop.
    # ---------------------------------------------------------------
    result = bind.execute(
        sa.text(
            "SELECT income_id, payment_method FROM incomes "
            "WHERE payment_method IS NOT NULL "
            "  AND upper(payment_method) NOT IN :allowed",
        ),
        {"allowed": ALLOWED_PAYMENT_METHODS},
    )
    offending = result.fetchall()
    if offending:
        rows = [f"  income_id={r[0]}, payment_method={r[1]!r}" for r in offending]
        raise RuntimeError(
            "Migration aborted: the following existing income rows have payment_method "
            "values that would violate the new constraint. Resolve them manually before "
            "running this migration:\n" + "\n".join(rows)
        )

    # ---------------------------------------------------------------
    # Drop old constraint
    # ---------------------------------------------------------------
    op.drop_constraint(
        "incomes_payment_method_check",
        "incomes",
        type_="check",
    )

    # ---------------------------------------------------------------
    # Create the corrected constraint.
    # Uses upper() so existing mixed-case values are also covered.
    # ---------------------------------------------------------------
    allowed_literals = ", ".join(f"'{v}'" for v in ALLOWED_PAYMENT_METHODS)
    op.create_check_constraint(
        "incomes_payment_method_check",
        "incomes",
        f"payment_method IS NULL OR upper(payment_method) = ANY (ARRAY[{allowed_literals}])",
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Drop the new constraint
    op.drop_constraint(
        "incomes_payment_method_check",
        "incomes",
        type_="check",
    )

    # Restore the original constraint (exactly as it was in production)
    op.create_check_constraint(
        "incomes_payment_method_check",
        "incomes",
        (
            "payment_method IS NULL OR upper(payment_method) = ANY ("
            "ARRAY['SALARY', 'CASH', 'BANK_TRANSFER', 'BANK TRANSFER', "
            "'UPI', 'DEBIT_CARD', 'DEBIT CARD', 'CREDIT_CARD', "
            "'CREDIT CARD', 'CHEQUE', 'OTHER'])"
        ),
    )
