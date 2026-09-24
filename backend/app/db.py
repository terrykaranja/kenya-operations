"""Database configuration and session management.

Defaults to the SQLite file declared in DATABASE_URL (see .env.example);
set DATABASE_URL to a postgresql:// URL to run against PostgreSQL instead.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.resources import RESOURCES_DIR

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{RESOURCES_DIR / 'sez_ledger.db'}")

# SQLite needs this relaxed so the same connection can be used across the
# request/session boundary FastAPI's dependency injection creates.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
