"""Verify demo seed idempotency and stable SKU identity."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.database.engine import create_engine
from app.database.seed import PRODUCTS, seed_agent_data
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
    """Run seed repeatedly and verify the demo catalog remains stable."""

    async def test_triple_seed_stable_counts_and_skus(
        self, db_session: AsyncSession,
    ) -> None:
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

        referenced_product = await db_session.execute(text(
            "SELECT oi.product_id FROM order_items oi "
            "JOIN orders o ON o.id = oi.order_id WHERE o.order_number = 'ORD-000001'"
        ))
        referenced_product_id = referenced_product.scalar_one()

        await run_seed()
        await run_seed()
        db_session.expire_all()

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
            f"Seed not idempotent:\n  Run 1: {counts_1}\n  Run 3: {counts_2}"
        )

        # Verify minimum expected data
        assert counts_1["users"] >= 2, f"Expected >=2 users, got {counts_1['users']}"
        assert counts_1["products"] >= 10, f"Expected >=10 products, got {counts_1['products']}"
        assert counts_1["orders"] >= 3, f"Expected >=3 orders, got {counts_1['orders']}"
        assert counts_1["logistics_records"] >= 1, f"Expected >=1 logistics, got {counts_1['logistics_records']}"
        assert counts_1["agent_sessions"] >= 1, f"Expected >=1 agent session, got {counts_1['agent_sessions']}"

        demo_skus = [str(product["sku"]) for product in PRODUCTS]
        sku_stats = await db_session.execute(text(
            "SELECT COUNT(*), COUNT(DISTINCT sku), "
            "COUNT(DISTINCT split_part(sku, '-', 2)) "
            "FROM products WHERE is_active = TRUE AND sku = ANY(:skus)"
        ), {"skus": demo_skus})
        assert sku_stats.one() == (23, 23, 6)

        duplicate_skus = await db_session.execute(text(
            "SELECT COUNT(*) FROM ("
            "SELECT sku FROM products WHERE sku = ANY(:skus) "
            "GROUP BY sku HAVING COUNT(*) > 1) duplicate"
        ), {"skus": demo_skus})
        assert duplicate_skus.scalar_one() == 0

        referenced_after = await db_session.execute(text(
            "SELECT oi.product_id FROM order_items oi "
            "JOIN orders o ON o.id = oi.order_id WHERE o.order_number = 'ORD-000001'"
        ))
        assert referenced_after.scalar_one() == referenced_product_id

        demo_logistics = await db_session.execute(text(
            "SELECT COUNT(*) FROM logistics_records l "
            "JOIN orders o ON o.id = l.order_id "
            "WHERE o.order_number IN ('ORD-000001', 'ORD-000003')"
        ))
        assert demo_logistics.scalar() == 2

    async def test_seed_agent_data_tolerates_multiple_existing_sessions(
        self, db_session: AsyncSession,
    ) -> None:
        """Container startup must remain idempotent after normal demo usage."""
        from sqlalchemy import select

        from app.models.agent_session import AgentSession
        from app.models.user import User

        result = await db_session.execute(
            select(User).where(User.email == "demo@example.com")
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            await run_seed()
            result = await db_session.execute(
                select(User).where(User.email == "demo@example.com")
            )
            customer = result.scalar_one()

        db_session.add_all([
            AgentSession(user_id=customer.id),
            AgentSession(user_id=customer.id),
        ])
        await db_session.commit()

        await seed_agent_data(db_session, {customer.email: customer})
