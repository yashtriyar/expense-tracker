"""
schemas.py — Pydantic v2 schemas for request/response validation.

These act as the API contract layer (FastAPI-ready) and keep Pydantic
completely decoupled from SQLAlchemy models.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ---------------------------------------------------------------------------
# Input schema (what the caller supplies)
# ---------------------------------------------------------------------------

# Realistic ceiling for a personal expense: ₹1,00,00,000 (1 crore).
# Prevents astronomically large values that overflow float in the UI.
_MAX_AMOUNT = Decimal("10000000.00")

class ExpenseCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Must be a positive value")
    category: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    date: date

    @field_validator("category")
    @classmethod
    def category_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("category cannot be blank")
        return v

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        """Accept int / float / str and coerce to Decimal safely."""
        try:
            d = Decimal(str(v))
        except Exception:
            raise ValueError(f"Cannot parse amount: {v!r}")
        if d > _MAX_AMOUNT:
            raise ValueError(f"Amount cannot exceed ₹{_MAX_AMOUNT:,}")
        # Reject more than 2 decimal places (e.g. 1.999 is not valid money)
        if d != d.quantize(Decimal("0.01")):
            raise ValueError("Amount must have at most 2 decimal places")
        return d

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# Output schema (what is returned to the caller)
# ---------------------------------------------------------------------------

class ExpenseOut(BaseModel):
    id: str
    amount: Decimal
    category: str
    description: str
    date: date
    created_at: datetime
    idempotency_key: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v):
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Filter / query params schema
# ---------------------------------------------------------------------------

class ExpenseFilter(BaseModel):
    category: Optional[str] = None
    sort: Optional[str] = None  # e.g. "date_desc"