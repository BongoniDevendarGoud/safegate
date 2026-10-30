"""
SafeGate — Database Engine & Session Management
================================================
This module initializes the SQLAlchemy ORM layer for SQLite.

VIVA EXPLANATION / CORE CONCEPTS:
1. Engine: Represents the core interface to the SQLite database file.
   `check_same_thread=False` allows FastAPI's multi-threaded async workers
   to query SQLite safely while each worker operates within its own session.
2. DeclarativeBase: Serves as the metaclass registry mapping Python classes
   to database tables.
3. Dependency Injection (`get_db`): FastAPI injects a clean database session
   into each request using Python generators with a `finally: session.close()`
   guarantee, preventing connection leaks.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.config import settings

# Create database engine using the configured connection URL
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False,  # Set to True only during deep SQL debugging
)

# Thread-local session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base from which all ORM entities inherit
Base = declarative_base()


def init_db() -> None:
    """
    Idempotent database schema creation.
    
    Invoked on application startup to ensure tables (Uploads, Blocklists,
    AuditLog, Appeals) exist before incoming requests are received.
    """
    # Import models here so Base registers all schema metadata before create_all
    import app.models.database  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per HTTP request.
    
    Ensures that every request runs in an isolated transaction and the session
    is cleanly closed in a `finally` block when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
