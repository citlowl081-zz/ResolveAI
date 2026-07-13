"""Async SQLAlchemy engine creation."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config.settings import settings


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Args:
        database_url: Override the default DATABASE_URL from settings.
    """
    url = database_url or settings.resolved_database_url
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
