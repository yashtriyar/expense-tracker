"""
models.py — SQLAlchemy ORM table definitions.

Rule: no business logic here — only table structure.
Decimal is stored as a NUMERIC column so SQLite preserves precision.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import String, Numeric, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    amount: Mapped[str] = mapped_column(
        # Store as String to guarantee Decimal fidelity across SQLite versions.
        # We convert to/from Decimal in the CRUD layer.
        String(30), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Expense id={self.id} amount={self.amount} category={self.category}>"
