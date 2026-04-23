"""
tests/test_crud.py — Unit tests for core business logic.

Uses an in-memory SQLite database so tests are fast, isolated, and require
no filesystem setup.

Run with:
    pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base
from backend import models  # noqa: F401 — needed to register tables
from backend import crud
from backend.schemas import ExpenseCreate
from backend.idempotency import generate_key


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db():
    """In-memory SQLite session, fresh per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _make_payload(**overrides) -> ExpenseCreate:
    defaults = dict(
        amount=Decimal("150.00"),
        category="Food & Dining",
        description="Test lunch",
        date=datetime.date(2024, 6, 15),
    )
    defaults.update(overrides)
    return ExpenseCreate(**defaults)


# ---------------------------------------------------------------------------
# create_expense — happy path
# ---------------------------------------------------------------------------

def test_create_expense_success(db):
    payload = _make_payload()
    expense, created = crud.create_expense(db, payload)

    assert created is True
    assert expense.amount == Decimal("150.00")
    assert expense.category == "Food & Dining"
    assert expense.description == "Test lunch"
    assert expense.date == datetime.date(2024, 6, 15)
    assert expense.id is not None
    assert expense.idempotency_key is not None


# ---------------------------------------------------------------------------
# Idempotency — duplicate is silently de-duped
# ---------------------------------------------------------------------------

def test_create_expense_duplicate_returns_existing(db):
    payload = _make_payload()

    expense1, created1 = crud.create_expense(db, payload)
    expense2, created2 = crud.create_expense(db, payload)

    assert created1 is True
    assert created2 is False
    assert expense1.id == expense2.id  # same record returned


def test_idempotency_key_is_deterministic():
    key1 = generate_key(Decimal("100"), "Food", "lunch", datetime.date(2024, 1, 1))
    key2 = generate_key(Decimal("100"), "Food", "lunch", datetime.date(2024, 1, 1))
    assert key1 == key2
    assert len(key1) == 64


def test_idempotency_key_differs_on_different_inputs():
    k1 = generate_key(Decimal("100"), "Food", "lunch", datetime.date(2024, 1, 1))
    k2 = generate_key(Decimal("200"), "Food", "lunch", datetime.date(2024, 1, 1))
    assert k1 != k2


# ---------------------------------------------------------------------------
# Validation — negative / zero amounts
# ---------------------------------------------------------------------------

def test_create_expense_rejects_negative_amount(db):
    with pytest.raises(Exception):
        # Pydantic will reject before crud even runs
        payload = _make_payload(amount=Decimal("-50"))
        crud.create_expense(db, payload)


def test_create_expense_rejects_zero_amount(db):
    with pytest.raises(Exception):
        payload = _make_payload(amount=Decimal("0"))
        crud.create_expense(db, payload)


# ---------------------------------------------------------------------------
# get_expenses — filtering and sorting
# ---------------------------------------------------------------------------

def test_get_expenses_returns_all(db):
    crud.create_expense(db, _make_payload(category="Food & Dining"))
    crud.create_expense(db, _make_payload(category="Transport", description="Bus"))
    expenses = crud.get_expenses(db)
    assert len(expenses) == 2


def test_get_expenses_filters_by_category(db):
    crud.create_expense(db, _make_payload(category="Food & Dining"))
    crud.create_expense(db, _make_payload(category="Transport", description="Bus"))
    expenses = crud.get_expenses(db, category="Transport")
    assert len(expenses) == 1
    assert expenses[0].category == "Transport"


def test_get_expenses_sorted_newest_first(db):
    crud.create_expense(db, _make_payload(date=datetime.date(2024, 1, 1), description="old"))
    crud.create_expense(db, _make_payload(date=datetime.date(2024, 6, 1), description="new"))
    expenses = crud.get_expenses(db, sort="date_desc")
    assert expenses[0].date > expenses[1].date


def test_get_expenses_sorted_oldest_first(db):
    crud.create_expense(db, _make_payload(date=datetime.date(2024, 1, 1), description="old"))
    crud.create_expense(db, _make_payload(date=datetime.date(2024, 6, 1), description="new"))
    expenses = crud.get_expenses(db, sort="date_asc")
    assert expenses[0].date < expenses[1].date


# ---------------------------------------------------------------------------
# get_total — Decimal arithmetic
# ---------------------------------------------------------------------------

def test_get_total_uses_decimal(db):
    crud.create_expense(db, _make_payload(amount=Decimal("100.10"), description="a"))
    crud.create_expense(db, _make_payload(amount=Decimal("200.20"), description="b"))
    expenses = crud.get_expenses(db)
    total = crud.get_total(expenses)
    assert total == Decimal("300.30")
    assert isinstance(total, Decimal)


def test_get_total_empty_list():
    total = crud.get_total([])
    assert total == Decimal("0")


# ---------------------------------------------------------------------------
# category_summary
# ---------------------------------------------------------------------------

def test_category_summary(db):
    crud.create_expense(db, _make_payload(amount=Decimal("100"), category="Food & Dining", description="a"))
    crud.create_expense(db, _make_payload(amount=Decimal("50"), category="Transport", description="b"))
    crud.create_expense(db, _make_payload(amount=Decimal("75"), category="Food & Dining", description="c"))
    expenses = crud.get_expenses(db)
    summary = crud.get_category_summary(expenses)
    assert summary["Food & Dining"] == Decimal("175")
    assert summary["Transport"] == Decimal("50")
