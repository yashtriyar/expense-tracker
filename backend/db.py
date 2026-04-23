"""
db.py — Database engine and session factory.

Separation of concern: this module owns only the SQLAlchemy lifecycle.
Nothing business-logic-related belongs here.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Store the SQLite file one level above backend/ so it survives re-installs
_DB_PATH = Path(__file__).resolve().parent.parent / "expenses.db"
DATABASE_URL = f"sqlite:///{_DB_PATH}"

# check_same_thread=False is required for SQLite when used with Streamlit
# because Streamlit may call DB operations from different threads.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # set True to debug SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db():
    """
    Context-manager-style session provider.
    Usage:
        db = next(get_db())
    Or in a with-block via contextlib.closing.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist yet. Safe to call on every startup."""
    # Import models here so Base is populated before create_all
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
