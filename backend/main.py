"""
main.py — Optional FastAPI application.

This file is NOT used by the Streamlit frontend (which calls crud.py directly).
It exists to demonstrate that the backend is FastAPI-ready and can be deployed
as a standalone HTTP service with zero changes to crud.py.

Run with:
    uvicorn backend.main:app --reload
"""

from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db import get_db, init_db
from backend import crud
from backend.schemas import ExpenseCreate, ExpenseOut

app = FastAPI(
    title="Expense Tracker API",
    description="Production-quality expense tracking with idempotency",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
):
    try:
        expense, created = crud.create_expense(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return expense


@app.get("/expenses", response_model=List[ExpenseOut])
def list_expenses(
    category: Optional[str] = Query(None),
    sort: Optional[str] = Query(None, description="date_desc | date_asc"),
    db: Session = Depends(get_db),
):
    return crud.get_expenses(db, category=category, sort=sort)


@app.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: str, db: Session = Depends(get_db)):
    expense = crud.get_expense_by_id(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@app.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: str, db: Session = Depends(get_db)):
    deleted = crud.delete_expense(db, expense_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Expense not found")


@app.get("/expenses/meta/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    return crud.get_all_categories(db)


@app.get("/health")
def health():
    return {"status": "ok"}
