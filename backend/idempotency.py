"""
idempotency.py — Idempotency key generation.

A deterministic hash of the business-meaningful fields prevents duplicate
records when the user double-clicks, the network retries, or the page
refreshes mid-flight.

Design choice: SHA-256 (first 64 hex chars) is collision-resistant for
our domain and fits a VARCHAR(64) column.
"""

import hashlib
from datetime import date
from decimal import Decimal


def generate_key(amount: Decimal, category: str, description: str, expense_date: date) -> str:
    """
    Return a 64-character hex digest that uniquely identifies an expense
    defined by its core business fields.

    NOTE: Two expenses with identical fields on the same day are treated as
    the same event. If you need to allow identical amounts/categories on the
    same day, you must add a user-supplied nonce to the payload.
    """
    # Normalize amount to a canonical string: remove trailing zeros so that
    # 12.34, 12.340, and 12.3400 all hash identically.
    # quantize(Decimal("0.01")) rounds to 2 decimal places first, then
    # normalize() strips trailing zeros, giving a consistent representation.
    canonical_amount = str(amount.quantize(Decimal("0.01")).normalize())

    raw = "|".join([
        canonical_amount,
        category.strip().lower(),
        description.strip().lower(),
        expense_date.isoformat(),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()