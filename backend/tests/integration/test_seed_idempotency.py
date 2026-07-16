"""Verify seed script idempotency — double execution produces stable data counts."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.database.engine import create_engine
from app.database.seed import main as run_seed


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_engine(settings.resolved_database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _count(session: AsyncSession, table: str) -> int:
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    val = result.scalar()
    return int(val) if val is not None else 0


class TestSeedIdempotency:
    """Run seed twice, verify data counts are stable."""

    async def test_double_seed_stable_counts(self, db_session: AsyncSession) -> None:
        # First run
        await run_seed()
        await db_session.commit()

        counts_1 = {
            "users": await _count(db_session, "users"),
            "products": await _count(db_session, "products"),
            "orders": await _count(db_session, "orders"),
            "order_items": await _count(db_session, "order_items"),
            "logistics_records": await _count(db_session, "logistics_records"),
            "agent_sessions": await _count(db_session, "agent_sessions"),
            "agent_messages": await _count(db_session, "agent_messages"),
        }

        # Second run (idempotent)
        await run_seed()
        await db_session.commit()

        counts_2 = {
            "users": await _count(db_session, "users"),
            "products": await _count(db_session, "products"),
            "orders": await _count(db_session, "orders"),
            "order_items": await _count(db_session, "order_items"),
            "logistics_records": await _count(db_session, "logistics_records"),
            "agent_sessions": await _count(db_session, "agent_sessions"),
            "agent_messages": await _count(db_session, "agent_messages"),
        }

        assert counts_1 == counts_2, (
            f"Seed not idempotent:\n  Run 1: {counts_1}\n  Run 2: {counts_2}"
        )

        # Verify minimum expected data
        assert counts_1["users"] >= 2, f"Expected >=2 users, got {counts_1['users']}"
        assert counts_1["products"] >= 10, f"Expected >=10 products, got {counts_1['products']}"
        assert counts_1["orders"] >= 3, f"Expected >=3 orders, got {counts_1['orders']}"
        assert counts_1["logistics_records"] >= 1, f"Expected >=1 logistics, got {counts_1['logistics_records']}"
        assert counts_1["agent_sessions"] >= 1, f"Expected >=1 agent session, got {counts_1['agent_sessions']}"
