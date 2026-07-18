"""Database configuration and session management.

Provides async SQLAlchemy engine, session factory, and base model class.
"""

from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin that adds a UUID primary key column."""

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )


# Engine and session factory (initialized at runtime)
_engine = None
_session_factory = None


def init_db(database_url: str) -> None:
    """Initialize the database engine and session factory.

    Args:
        database_url: The async database connection URL.
    """
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Yields:
        AsyncSession: An async database session.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Close the database engine and connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


def get_engine():
    """Get the current database engine.

    Returns:
        The async engine instance.
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory():
    """Get the current session factory.

    Returns:
        The async session factory.

    Raises:
        RuntimeError: If database is not initialized.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


def async_session_maker():
    """Get a new async session (for Celery tasks).

    Returns:
        AsyncSession instance.
    """
    factory = get_session_factory()
    return factory()
