"""
crud.py — All database operations live here and nowhere else.

Rules:
  - Accepts/returns Pydantic schemas or plain Python types (never raw ORM rows
    outside this module unless explicitly needed by the caller).
  - Never imports from frontend/.
  - Never raises HTTP exceptions — raises plain Python exceptions so the
    caller (Streamlit or FastAPI) can translate them.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models
from backend.idempotency import generate_key
from backend.schemas import ExpenseCreate, ExpenseOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _orm_to_schema(expense: models.Expense) -> ExpenseOut:
    return ExpenseOut.model_validate(expense)


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_expense(
    db: Session, expense_data: ExpenseCreate
) -> Tuple[ExpenseOut, bool]:
    """
    Insert a new expense or return the existing one if the idempotency key
    already exists.

    Returns:
        (ExpenseOut, created: bool)
        created=False means a duplicate was detected and the existing record
        is returned unchanged.

    Raises:
        ValueError: if business validation fails.
    """
    if expense_data.amount <= 0:
        raise ValueError(f"Amount must be positive, got {expense_data.amount}")
    if expense_data.date is None:
        raise ValueError("Expense date is required")

    idem_key = generate_key(
        expense_data.amount,
        expense_data.category,
        expense_data.description,
        expense_data.date,
    )

    # --- idempotency check ---------------------------------------------------
    existing = (
        db.query(models.Expense)
        .filter(models.Expense.idempotency_key == idem_key)
        .first()
    )
    if existing:
        return _orm_to_schema(existing), False

    # --- insert --------------------------------------------------------------
    db_expense = models.Expense(
        id=str(uuid.uuid4()),
        amount=str(expense_data.amount),   # store as string for Decimal safety
        category=expense_data.category.strip(),
        description=expense_data.description.strip(),
        date=expense_data.date,
        idempotency_key=idem_key,
    )
    db.add(db_expense)

    try:
        db.commit()
        db.refresh(db_expense)
    except IntegrityError:
        # Race condition: another process inserted the same key between our
        # check and our insert.  Roll back and return the winner's record.
        db.rollback()
        existing = (
            db.query(models.Expense)
            .filter(models.Expense.idempotency_key == idem_key)
            .first()
        )
        if existing:
            return _orm_to_schema(existing), False
        raise  # truly unexpected; re-raise

    return _orm_to_schema(db_expense), True


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_expenses(
    db: Session,
    category: Optional[str] = None,
    sort: Optional[str] = None,
) -> List[ExpenseOut]:
    """
    Fetch expenses with optional category filter and sort.

    Args:
        category: if provided, case-insensitive exact match.
        sort: "date_desc" → newest first (default behaviour).
    """
    query = db.query(models.Expense)

    if category:
        query = query.filter(
            models.Expense.category.ilike(category.strip())
        )

    # Default: newest first
    if sort == "date_asc":
        query = query.order_by(models.Expense.date.asc(), models.Expense.created_at.asc())
    else:
        query = query.order_by(models.Expense.date.desc(), models.Expense.created_at.desc())

    return [_orm_to_schema(row) for row in query.all()]


def get_expense_by_id(db: Session, expense_id: str) -> Optional[ExpenseOut]:
    row = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    return _orm_to_schema(row) if row else None


def get_all_categories(db: Session) -> List[str]:
    """Return sorted distinct categories present in the DB."""
    rows = db.query(models.Expense.category).distinct().all()
    return sorted({r[0] for r in rows})


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def get_total(expenses: List[ExpenseOut]) -> Decimal:
    """
    Sum amounts using Decimal arithmetic.
    Always returns Decimal, never float, to avoid rounding errors.
    """
    return sum((e.amount for e in expenses), Decimal("0"))


def get_category_summary(expenses: List[ExpenseOut]) -> dict[str, Decimal]:
    """Group expenses by category and return {category: total} mapping."""
    summary: dict[str, Decimal] = {}
    for exp in expenses:
        summary[exp.category] = summary.get(exp.category, Decimal("0")) + exp.amount
    return dict(sorted(summary.items(), key=lambda kv: kv[1], reverse=True))


# ---------------------------------------------------------------------------
# Delete (for completeness / future use)
# ---------------------------------------------------------------------------

def delete_expense(db: Session, expense_id: str) -> bool:
    """Returns True if deleted, False if not found."""
    row = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
