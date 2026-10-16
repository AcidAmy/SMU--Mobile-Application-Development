"""
Database setup and session management using SQLAlchemy and SQLite.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

try:
    from .config import settings
except ImportError:
    from config import settings

# SQLite requires check_same_thread=False when used across multiple FastAPI threads
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Ensures that the session is properly closed after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Creates all database tables defined in models.py if they don't already exist.
    """
    try:
        from . import models  # noqa: F401
    except ImportError:
        import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
