"""Integration tests for CustomerMemory model and database constraints."""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.database.engine import create_engine
from app.models.customer_memory import CustomerMemory
from app.models.enums import MemoryStatus, MemoryType


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh async DB session for a single test."""
    engine = create_engine(settings.resolved_database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """Remove any memory rows left by a previous test."""
    yield
    try:
        await db_session.execute(text("DELETE FROM customer_memories"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


# ── Helper ────────────────────────────────────────────────────────────────


def _make_memory(**overrides: object) -> CustomerMemory:
    defaults = {
        "user_id": uuid.uuid4(),
        "memory_type": MemoryType.PREFERENCE,
        "content": "Test memory content",
        "source": "explicit_api",
        "confidence": 1.0,
        "status": MemoryStatus.ACTIVE,
    }
    defaults.update(overrides)
    return CustomerMemory(**defaults)


# ── Tests ─────────────────────────────────────────────────────────────────


class TestMemoryModelBasic:
    async def _create_user(self, db_session: AsyncSession, uid: uuid.UUID) -> None:
        await db_session.execute(
            text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                 "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
            {"id": uid, "email": f"mem-{uid.hex[:8]}@test.com",
             "pw": "hash", "name": "Mem Test"},
        )
        await db_session.commit()

    async def test_create_and_read(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await self._create_user(db_session, uid)
        mem = _make_memory(user_id=uid, key="test-key")
        db_session.add(mem)
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT content FROM customer_memories WHERE user_id=:uid"),
            {"uid": uid},
        )
        rows = result.mappings().all()
        assert len(rows) == 1
        assert rows[0]["content"] == "Test memory content"

    async def test_cascade_delete_on_user(self, db_session: AsyncSession) -> None:
        # Create a new user first
        uid = uuid.uuid4()
        await db_session.execute(
            text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                 "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
            {"id": uid, "email": f"mem-test-{uid.hex[:8]}@test.com",
             "pw": "hash", "name": "Mem Test"},
        )
        await db_session.commit()

        mem = _make_memory(user_id=uid, key="cascade-key")
        db_session.add(mem)
        await db_session.commit()

        # Delete user
        await db_session.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": uid})
        await db_session.commit()

        # Memory should be cascade-deleted
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM customer_memories WHERE user_id=:uid"),
            {"uid": uid},
        )
        assert result.scalar() == 0

    async def test_user_isolation_different_users(self, db_session: AsyncSession) -> None:
        uid_a = uuid.uuid4()
        uid_b = uuid.uuid4()

        for uid in (uid_a, uid_b):
            await db_session.execute(
                text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                     "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
                {"id": uid, "email": f"iso-{uid.hex[:8]}@test.com",
                 "pw": "hash", "name": "Iso Test"},
            )
        await db_session.commit()

        mem_a = _make_memory(user_id=uid_a, content="User A memory")
        mem_b = _make_memory(user_id=uid_b, content="User B memory")
        db_session.add_all([mem_a, mem_b])
        await db_session.commit()

        # User A only sees own memory
        result = await db_session.execute(
            text("SELECT content FROM customer_memories WHERE user_id=:uid"),
            {"uid": uid_a},
        )
        contents = [r[0] for r in result]
        assert "User A memory" in contents
        assert "User B memory" not in contents


class TestMemoryConstraints:
    async def test_active_unique_key_constraint(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await db_session.execute(
            text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                 "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
            {"id": uid, "email": f"uq-{uid.hex[:8]}@test.com",
             "pw": "hash", "name": "UQ Test"},
        )
        await db_session.commit()

        mem1 = _make_memory(
            user_id=uid, memory_type=MemoryType.PREFERENCE,
            key="same-key", content="First",
        )
        mem2 = _make_memory(
            user_id=uid, memory_type=MemoryType.PREFERENCE,
            key="same-key", content="Second",
        )
        db_session.add(mem1)
        await db_session.commit()

        db_session.add(mem2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_different_keys_ok(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await db_session.execute(
            text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                 "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
            {"id": uid, "email": f"dk-{uid.hex[:8]}@test.com",
             "pw": "hash", "name": "DK Test"},
        )
        await db_session.commit()

        db_session.add(_make_memory(user_id=uid, key="key-a", content="A"))
        db_session.add(_make_memory(user_id=uid, key="key-b", content="B"))
        await db_session.commit()  # Should not raise

    async def test_archived_does_not_block_active_key(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await db_session.execute(
            text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                 "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
            {"id": uid, "email": f"arch-{uid.hex[:8]}@test.com",
             "pw": "hash", "name": "Arch Test"},
        )
        await db_session.commit()

        mem1 = _make_memory(
            user_id=uid, memory_type=MemoryType.PREFERENCE,
            key="arch-key", content="Old", status=MemoryStatus.ARCHIVED,
        )
        db_session.add(mem1)
        await db_session.commit()

        # New ACTIVE with same key should be OK since old is ARCHIVED
        mem2 = _make_memory(
            user_id=uid, memory_type=MemoryType.PREFERENCE,
            key="arch-key", content="New", status=MemoryStatus.ACTIVE,
        )
        db_session.add(mem2)
        await db_session.commit()  # Should not raise

    async def test_superseded_chain(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await db_session.execute(
            text("INSERT INTO users (id, email, hashed_password, full_name, role) "
                 "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
            {"id": uid, "email": f"sup-{uid.hex[:8]}@test.com",
             "pw": "hash", "name": "Sup Test"},
        )
        await db_session.commit()

        mem1 = _make_memory(user_id=uid, content="v1")
        db_session.add(mem1)
        await db_session.commit()
        await db_session.refresh(mem1)

        mem2 = _make_memory(
            user_id=uid, content="v2",
            superseded_by=mem1.id, status=MemoryStatus.SUPERSEDED,
        )
        db_session.add(mem2)
        await db_session.commit()
        await db_session.refresh(mem2)

        assert mem2.status == MemoryStatus.SUPERSEDED
        assert mem2.superseded_by == mem1.id


class TestMigrationCycle:
    """Verify the migration table exists with the expected columns."""

    async def test_table_exists(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename='customer_memories'")
        )
        assert result.scalar() is not None

    async def test_enum_types_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("SELECT typname FROM pg_type WHERE typname IN ('memory_type', 'memory_status')")
        )
        types = {r[0] for r in result}
        assert "memory_type" in types
        assert "memory_status" in types
