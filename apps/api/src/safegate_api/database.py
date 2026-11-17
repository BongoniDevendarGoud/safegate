"""
SafeGate Database Subsystem.
Configures SQLAlchemy 2.0 async engine, session factory, and declarative base.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from safegate_api.config import settings


class Base(DeclarativeBase):
    pass


from typing import Any
from sqlalchemy import event

# Global engine and sessionmaker
engine_kwargs: dict[str, Any] = {"echo": settings.debug}
if settings.database.url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"timeout": 60.0}
else:
    engine_kwargs["pool_size"] = settings.database.pool_size
    engine_kwargs["max_overflow"] = settings.database.max_overflow

engine: AsyncEngine = create_async_engine(
    settings.database.url,
    **engine_kwargs,
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    if settings.database.url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.close()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper providing an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
