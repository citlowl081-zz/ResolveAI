"""Integration tests for PolicyDocument and PolicyChunk model constraints.

All tests use real PostgreSQL + pgvector.  Each test is self-contained
and creates / cleans up its own data.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.database.engine import create_engine
from app.models.enums import PolicyStatus
from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument


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
    """Remove any policy rows left by a previous test."""
    yield
    try:
        await db_session.execute(text("DELETE FROM policy_chunks"))
        await db_session.execute(text("DELETE FROM policy_documents"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


# ── Helper ──────────────────────────────────────────────────────────────


def _make_doc(**overrides: object) -> PolicyDocument:
    defaults: dict = {
        "policy_key": f"POL-REF-{uuid.uuid4().hex[:3]}",
        "version": 1,
        "title": "Test Policy",
        "category": "REFUND",
        "content": "Test content for validation.",
        "effective_date": date(2025, 1, 1),
        "status": "DRAFT",
    }
    defaults.update({k: v for k, v in overrides.items() if v is not ...})
    return PolicyDocument(**defaults)


def _make_chunk(doc_id: uuid.UUID, chunk_index: int = 0) -> PolicyChunk:
    return PolicyChunk(
        policy_document_id=doc_id,
        chunk_index=chunk_index,
        content=f"Chunk {chunk_index} text.",
        embedding=[0.0] * 1536,
    )


# ── Fixture setup ───────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def persisted_doc(db_session: AsyncSession) -> PolicyDocument:
    """Create and commit a PolicyDocument, return it."""
    doc = _make_doc()
    db_session.add(doc)
    await db_session.commit()
    return doc


# ── PolicyDocument constraints ──────────────────────────────────────────


class TestPolicyDocumentUniqueKeyVersion:
    """UNIQUE(policy_key, version)."""

    async def test_same_key_version_rejected(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        """Two rows with the same (policy_key, version) → IntegrityError."""
        doc2 = _make_doc(
            policy_key=persisted_doc.policy_key,
            version=persisted_doc.version,
        )
        db_session.add(doc2)
        with pytest.raises(IntegrityError):  # IntegrityError
            await db_session.commit()
        await db_session.rollback()

    async def test_same_key_different_version_allowed(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        """Different versions of the same policy_key are allowed."""
        doc2 = _make_doc(
            policy_key=persisted_doc.policy_key,
            version=persisted_doc.version + 1,
        )
        db_session.add(doc2)
        await db_session.commit()  # must not raise


class TestPolicyDocumentActivePartialUnique:
    """At most one ACTIVE per policy_key (partial unique index)."""

    async def test_two_active_same_key_rejected(
        self, db_session: AsyncSession,
    ) -> None:
        doc1 = _make_doc(policy_key="POL-REF-001", version=1, status="ACTIVE")
        db_session.add(doc1)
        await db_session.commit()

        doc2 = _make_doc(policy_key="POL-REF-001", version=2, status="ACTIVE")
        db_session.add(doc2)
        with pytest.raises(IntegrityError):  # IntegrityError from partial unique index
            await db_session.commit()
        await db_session.rollback()

    async def test_multiple_non_active_same_key_allowed(
        self, db_session: AsyncSession,
    ) -> None:
        doc1 = _make_doc(policy_key="POL-REF-001", version=1, status="DRAFT")
        db_session.add(doc1)
        await db_session.commit()

        doc2 = _make_doc(policy_key="POL-REF-001", version=2, status="SUPERSEDED")
        db_session.add(doc2)
        await db_session.commit()

        doc3 = _make_doc(policy_key="POL-REF-001", version=3, status="ARCHIVED")
        db_session.add(doc3)
        await db_session.commit()  # none are ACTIVE — must succeed


class TestPolicyDocumentVersionCheck:
    """CHECK(version >= 1)."""

    async def test_version_zero_rejected(
        self, db_session: AsyncSession,
    ) -> None:
        doc = _make_doc(version=0)
        db_session.add(doc)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_version_negative_rejected(
        self, db_session: AsyncSession,
    ) -> None:
        doc = _make_doc(version=-1)
        db_session.add(doc)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


# ── PolicyChunk constraints ─────────────────────────────────────────────


class TestPolicyChunkUniqueDocIndex:
    """UNIQUE(policy_document_id, chunk_index)."""

    async def test_duplicate_chunk_index_rejected(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        chunk1 = _make_chunk(persisted_doc.id, 0)
        chunk2 = _make_chunk(persisted_doc.id, 0)  # same index
        db_session.add_all([chunk1, chunk2])
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_different_indices_allowed(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        chunk1 = _make_chunk(persisted_doc.id, 0)
        chunk2 = _make_chunk(persisted_doc.id, 1)
        db_session.add_all([chunk1, chunk2])
        await db_session.commit()  # must not raise


class TestPolicyChunkCascadeDelete:
    """ON DELETE CASCADE from policy_documents to policy_chunks."""

    async def test_delete_document_removes_chunks(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        chunk = _make_chunk(persisted_doc.id, 0)
        db_session.add(chunk)
        await db_session.commit()

        await db_session.delete(persisted_doc)
        await db_session.commit()

        result = await db_session.execute(
            select(PolicyChunk).where(PolicyChunk.id == chunk.id)
        )
        assert result.scalar_one_or_none() is None


class TestPolicyDocumentSupersededByFK:
    """superseded_by FK references policy_documents.id."""

    async def test_valid_superseded_by_reference(
        self, db_session: AsyncSession,
    ) -> None:
        doc1 = _make_doc(policy_key="POL-REF-001", version=1)
        db_session.add(doc1)
        await db_session.commit()

        doc2 = _make_doc(policy_key="POL-REF-001", version=2, status="ACTIVE")
        db_session.add(doc2)
        await db_session.commit()

        doc1.status = PolicyStatus.SUPERSEDED
        doc1.superseded_by = doc2.id
        await db_session.commit()  # must not raise

    async def test_invalid_superseded_by_rejected(
        self, db_session: AsyncSession,
    ) -> None:
        doc = _make_doc()
        doc.superseded_by = uuid.uuid4()  # non-existent UUID
        db_session.add(doc)
        with pytest.raises(IntegrityError):  # FK violation
            await db_session.commit()
        await db_session.rollback()


class TestPolicyChunkVectorDimension:
    """The embedding column is fixed at vector(1536)."""

    async def test_correct_dimension_stored(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        vec = [0.1] * 1536
        chunk = PolicyChunk(
            policy_document_id=persisted_doc.id,
            chunk_index=0,
            content="Test.",
            embedding=vec,
        )
        db_session.add(chunk)
        await db_session.commit()

        result = await db_session.execute(
            select(PolicyChunk).where(PolicyChunk.id == chunk.id)
        )
        row = result.scalar_one()
        assert len(row.embedding) == 1536

    async def test_wrong_dimension_rejected(
        self, db_session: AsyncSession, persisted_doc: PolicyDocument,
    ) -> None:
        vec = [0.1] * 768  # wrong dimension
        chunk = PolicyChunk(
            policy_document_id=persisted_doc.id,
            chunk_index=0,
            content="Test.",
            embedding=vec,
        )
        db_session.add(chunk)
        with pytest.raises(SQLAlchemyError):  # pgvector dimension mismatch
            await db_session.commit()
        await db_session.rollback()
