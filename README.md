# ₹ Expense Tracker

A minimal, production-quality expense tracking application built with Python only.

```
Backend  : FastAPI-style architecture (SQLAlchemy + Pydantic)
Frontend : Streamlit
Database : SQLite (file-based, persistent)
Language : Python 3.11+
```

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the app (from the expense_tracker/ directory)
streamlit run frontend/app.py

# 3. (Optional) Run the FastAPI server separately
uvicorn backend.main:app --reload

# 4. Run unit tests
pytest tests/ -v
```

---

## Project Structure

```
expense_tracker/
│
├── backend/
│   ├── __init__.py
│   ├── db.py          # Engine, session factory, Base
│   ├── models.py      # SQLAlchemy ORM table definitions
│   ├── schemas.py     # Pydantic input/output schemas
│   ├── crud.py        # All DB operations (no HTTP, no Streamlit)
│   ├── idempotency.py # Deterministic key generation (SHA-256)
│   └── main.py        # Optional FastAPI app (unused by Streamlit)
│
├── frontend/
│   └── app.py         # Streamlit UI — calls crud.py directly
│
├── tests/
│   └── test_crud.py   # Unit tests (in-memory SQLite)
│
├── requirements.txt
└── README.md
```

---

## Design Decisions

### Why SQLite?
- **Zero infrastructure**: no separate DB server to run, perfect for local/single-user deployment.
- **File-based persistence**: the `expenses.db` file survives restarts and can be copied/backed up trivially.
- **SQLAlchemy abstraction**: swapping to PostgreSQL/MySQL in the future requires changing only one line in `db.py` (`DATABASE_URL`).

### Why `Decimal` instead of `float`?
Financial arithmetic using IEEE-754 floats accumulates rounding errors:
```python
>>> 0.1 + 0.2
0.30000000000000004
```
`Decimal` gives exact base-10 arithmetic. We store amounts as `VARCHAR(30)` in SQLite (a Decimal-string) to guarantee round-trip fidelity regardless of SQLite's loose typing.

### Why Idempotency?
Three real-world failure modes are handled:
1. **Double-click** — user submits the form twice before the first response arrives.
2. **Page refresh** — browser re-sends the POST on F5.
3. **Retry logic** — automated retries after a transient error.

**Implementation**: A SHA-256 hash of `(amount + category + description + date)` is stored as a unique index. A second insert with the same key is short-circuited at the DB layer; the existing record is returned and the UI shows an informational banner instead of an error.

---

## Trade-offs

| Decision | Chosen | Alternative | Reason |
|---|---|---|---|
| Deployment | Single process (Streamlit calls crud directly) | Separate FastAPI + HTTP | Simpler ops; FastAPI app included for future split |
| Auth | None | JWT / OAuth | Out of scope; add middleware in `main.py` |
| DB | SQLite file | PostgreSQL | No infra needed; one-line change to upgrade |
| Amount storage | String in SQLite | NUMERIC column | String guarantees Decimal round-trip on all SQLite builds |
| Category | Preset list | Free-text | Reduces data inconsistency ("food" vs "Food") |

---

## Extending the App

- **Add authentication**: inject a `user_id` FK into the `expenses` table; add FastAPI OAuth2 middleware.
- **Switch to PostgreSQL**: update `DATABASE_URL` in `db.py`; change `amount` column to `NUMERIC(12, 2)`.
- **REST API only**: `backend/main.py` is already a complete FastAPI application — run it standalone and point any frontend at it.
- **Recurring expenses**: add a `recurrence` field and a scheduler (APScheduler) that clones the row periodically.
