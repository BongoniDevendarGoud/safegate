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

# Global engine and sessionmaker
engine_kwargs: dict[str, Any] = {"echo": settings.debug}
if not settings.database.url.startswith("sqlite"):
    engine_kwargs["pool_size"] = settings.database.pool_size
    engine_kwargs["max_overflow"] = settings.database.max_overflow

engine: AsyncEngine = create_async_engine(
    settings.database.url,
    **engine_kwargs,
)

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
