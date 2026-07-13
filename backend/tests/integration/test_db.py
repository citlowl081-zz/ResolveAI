"""Integration tests for database connectivity."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_session_executes_query(db_session: AsyncSession) -> None:
    """Database session can execute a simple SELECT query."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_session_rollback_on_error(db_session: AsyncSession) -> None:
    """Database session handles errors gracefully — explicit rollback required."""
    try:
        await db_session.execute(text("SELECT * FROM nonexistent_table"))
    except Exception:
        await db_session.rollback()
    # Session should still be usable after rollback
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
