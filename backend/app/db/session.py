"""Database session management and schema initialization."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.app.config import DATABASE_URL
from backend.app.db.tables import Base

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None) -> None:
    """Create all SQLite tables according to defined metadata."""
    e = target_engine or engine
    Base.metadata.create_all(bind=e)


# Ensure tables exist on database initialization
init_db()


def get_db() -> Generator[Session, None, None]:
    """FastAPI and context dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
