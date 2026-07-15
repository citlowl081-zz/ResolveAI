"""Integration tests for ApprovalTask model and database constraints."""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.database.engine import create_engine
from app.models.approval_task import ApprovalTask
from app.models.enums import ApprovalStatus, ApprovalType


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_engine(settings.resolved_database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    yield
    try:
        await db_session.execute(text("DELETE FROM approval_tasks"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


async def _create_user(db_session: AsyncSession, uid: uuid.UUID) -> None:
    await db_session.execute(
        text("INSERT INTO users (id, email, hashed_password, full_name, role) "
             "VALUES (:id, :email, :pw, :name, 'CUSTOMER')"),
        {"id": uid, "email": f"appr-{uid.hex[:8]}@test.com",
         "pw": "hash", "name": "Approval Test"},
    )
    await db_session.commit()


class TestApprovalModelBasic:
    async def test_create_and_read(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await _create_user(db_session, uid)

        task = ApprovalTask(
            user_id=uid,
            action_id=f"action-{uuid.uuid4().hex[:12]}",
            tool_name="create_after_sales_ticket",
            sanitized_action_payload={"intent": "QUALITY_REFUND", "items": []},
            approval_type=ApprovalType.HIGH_REFUND,
            status=ApprovalStatus.PENDING,
            risk_level="MEDIUM",
            requested_by=uid,
        )
        db_session.add(task)
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT status FROM approval_tasks WHERE user_id=:uid"),
            {"uid": uid},
        )
        rows = result.mappings().all()
        assert len(rows) == 1
        assert rows[0]["status"] == "PENDING"

    async def test_unique_action_id(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await _create_user(db_session, uid)
        action_id = f"action-{uuid.uuid4().hex[:12]}"

        task1 = ApprovalTask(
            user_id=uid, action_id=action_id,
            tool_name="create_after_sales_ticket",
            sanitized_action_payload={"intent": "QUALITY_REFUND"},
            approval_type=ApprovalType.HIGH_REFUND,
            status=ApprovalStatus.PENDING,
            requested_by=uid,
        )
        db_session.add(task1)
        await db_session.commit()

        task2 = ApprovalTask(
            user_id=uid, action_id=action_id,  # Same action_id
            tool_name="create_after_sales_ticket",
            sanitized_action_payload={"intent": "QUALITY_REFUND"},
            approval_type=ApprovalType.HIGH_REFUND,
            status=ApprovalStatus.PENDING,
            requested_by=uid,
        )
        db_session.add(task2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_cascade_delete_user(self, db_session: AsyncSession) -> None:
        uid = uuid.uuid4()
        await _create_user(db_session, uid)

        task = ApprovalTask(
            user_id=uid,
            action_id=f"action-{uuid.uuid4().hex[:12]}",
            tool_name="create_after_sales_ticket",
            sanitized_action_payload={},
            approval_type=ApprovalType.RISK_HIT,
            status=ApprovalStatus.PENDING,
            requested_by=uid,
        )
        db_session.add(task)
        await db_session.commit()

        await db_session.execute(text("DELETE FROM users WHERE id=:uid"), {"uid": uid})
        await db_session.commit()

        result = await db_session.execute(
            text("SELECT COUNT(*) FROM approval_tasks WHERE user_id=:uid"),
            {"uid": uid},
        )
        assert result.scalar() == 0


class TestMigrationCycle:
    async def test_table_exists(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename='approval_tasks'")
        )
        assert result.scalar() is not None

    async def test_enum_types_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("SELECT typname FROM pg_type WHERE typname IN ('approval_status', 'approval_type')")
        )
        types = {r[0] for r in result}
        assert "approval_status" in types
        assert "approval_type" in types
