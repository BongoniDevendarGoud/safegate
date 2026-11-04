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
    Idempotent database schema creation and migration.
    
    Invoked on application startup to ensure tables (Uploads, Blocklists,
    AuditLog, Appeals, VideoFrames) exist and all required columns are present.
    """
    # Import models here so Base registers all schema metadata before create_all
    import app.models.database  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Safe SQLite column migration for existing databases
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "uploads" in inspector.get_table_names():
            existing_cols = {c["name"] for c in inspector.get_columns("uploads")}
            new_columns = [
                ("title", "VARCHAR(255)"),
                ("description", "TEXT"),
                ("duration_sec", "FLOAT"),
                ("fps", "FLOAT"),
                ("width", "INTEGER"),
                ("height", "INTEGER"),
                ("total_frames", "INTEGER DEFAULT 0"),
                ("extracted_frames", "INTEGER DEFAULT 0"),
                ("classified_frames", "INTEGER DEFAULT 0"),
                ("failed_frames", "INTEGER DEFAULT 0"),
                ("legitimate_frames_count", "INTEGER DEFAULT 0"),
                ("suspicious_frames_count", "INTEGER DEFAULT 0"),
                ("uncertain_frames_count", "INTEGER DEFAULT 0"),
                ("risk_score", "INTEGER DEFAULT 0"),
                ("publishing_status", "VARCHAR(32) DEFAULT 'unpublished'"),
                ("suspicious_segments", "TEXT"),
                ("model_name", "VARCHAR(128)"),
                ("model_status", "VARCHAR(64) DEFAULT 'active'"),
                ("security_report_json", "TEXT"),
            ]
            with engine.connect() as conn:
                for col_name, col_type in new_columns:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE uploads ADD COLUMN {col_name} {col_type}"))
                conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Database column migration note: %s", e)


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
