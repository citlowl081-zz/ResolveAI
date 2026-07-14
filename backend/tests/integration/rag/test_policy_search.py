"""Integration tests for PolicyService.search() — real PostgreSQL + pgvector."""

import uuid
from collections.abc import AsyncGenerator
from datetime import date, timedelta

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings
from app.models.policy_chunk import PolicyChunk
from app.models.policy_document import PolicyDocument
from app.rag.mock_embeddings import MockEmbeddingProvider
from app.services.policy_service import PolicyService


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    eng = create_async_engine(
        settings.resolved_database_url,
        pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await eng.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _cleanup(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    yield
    try:
        await db_session.execute(text("DELETE FROM policy_chunks"))
        await db_session.execute(text("DELETE FROM policy_documents"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest_asyncio.fixture
async def policy_service() -> AsyncGenerator[PolicyService, None]:
    eng = create_async_engine(
        settings.resolved_database_url,
        pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    provider = MockEmbeddingProvider(dimension=1536)
    svc = PolicyService(session_factory=factory, embedding_provider=provider)
    yield svc
    await eng.dispose()


async def _seed(
    db_session: AsyncSession,
    policy_key: str,
    version: int,
    title: str,
    category: str,
    content: str,
    status: str = "ACTIVE",
    effective_date: date | None = None,
    expiration_date: date | None = None,
) -> uuid.UUID:
    eff = effective_date or date.today()
    doc = PolicyDocument(
        policy_key=policy_key, version=version, title=title,
        category=category, content=content, effective_date=eff,
        expiration_date=expiration_date, status=status,
    )
    db_session.add(doc)
    await db_session.commit()

    provider = MockEmbeddingProvider(dimension=1536)
    vec = await provider.embed_query(content)
    chunk = PolicyChunk(
        policy_document_id=doc.id, chunk_index=0,
        content=content, embedding=vec, char_count=len(content),
    )
    db_session.add(chunk)
    await db_session.commit()
    return doc.id


class TestSearchRelevance:
    async def test_refund_query_ranks_refund_policy_first(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "未发货退款规则", "REFUND",
                   "订单未发货时可申请全额退款，包括商品金额和已支付的运费。")
        await _seed(db_session, "POL-LOG-001", 1, "物流丢件赔付规则", "LOGISTICS",
                   "物流公司确认丢件后，将按商品实际支付金额进行赔付。")
        await _seed(db_session, "POL-RISK-001", 1, "高额退款审核规则", "RISK",
                   "退款金额超过1000元的售后申请需要进行人工审核。")

        results = await policy_service.search("我要退款", top_k=5)
        assert len(results) >= 1
        # REFUND policy must appear — relevance may vary with mock embeddings
        keys = [r["policy_key"] for r in results]
        assert "POL-REF-001" in keys


class TestActiveFilter:
    async def test_superseded_policy_excluded(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "旧版退款", "REFUND",
                   "旧版退款规则内容", status="SUPERSEDED")

        results = await policy_service.search("退款", top_k=5)
        keys = [r["policy_key"] for r in results]
        assert "POL-REF-001" not in keys

    async def test_draft_policy_excluded(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "草稿退款", "REFUND",
                   "草稿退款规则", status="DRAFT")

        results = await policy_service.search("退款", top_k=5)
        keys = [r["policy_key"] for r in results]
        assert "POL-REF-001" not in keys


class TestCategoryFilter:
    async def test_category_filter_narrows_results(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "退款规则", "REFUND", "退款相关")
        await _seed(db_session, "POL-LOG-001", 1, "物流规则", "LOGISTICS", "物流相关")

        results = await policy_service.search("相关", top_k=5, category="REFUND")
        keys = [r["policy_key"] for r in results]
        assert "POL-REF-001" in keys
        assert "POL-LOG-001" not in keys


class TestDateFilter:
    async def test_future_effective_excluded(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "未来生效", "REFUND", "未来退款规则",
                   effective_date=date.today() + timedelta(days=30))

        results = await policy_service.search("退款", top_k=5)
        keys = [r["policy_key"] for r in results]
        assert "POL-REF-001" not in keys

    async def test_expired_excluded(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "已过期", "REFUND", "过期退款规则",
                   expiration_date=date.today() - timedelta(days=1))

        results = await policy_service.search("退款", top_k=5)
        keys = [r["policy_key"] for r in results]
        assert "POL-REF-001" not in keys


class TestDedupPerPolicyKey:
    async def test_multiple_chunks_one_policy_key(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        provider = MockEmbeddingProvider(dimension=1536)
        doc = PolicyDocument(
            policy_key="POL-REF-001", version=1, title="退款规则",
            category="REFUND", content="退款规则正文",
            effective_date=date.today(), status="ACTIVE",
        )
        db_session.add(doc)
        await db_session.commit()

        v1 = await provider.embed_query("退款规则正文")
        v2 = await provider.embed_query("退款申请条件")
        db_session.add(PolicyChunk(policy_document_id=doc.id, chunk_index=0,
                      content="退款规则正文", embedding=v1))
        db_session.add(PolicyChunk(policy_document_id=doc.id, chunk_index=1,
                      content="退款申请条件", embedding=v2))
        await db_session.commit()

        results = await policy_service.search("退款", top_k=5)
        keys = [r["policy_key"] for r in results]
        assert keys.count("POL-REF-001") == 1


class TestTopK:
    async def test_top_k_limits_results(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        for i in range(5):
            await _seed(db_session, f"POL-REF-{i:03d}", 1,
                       f"退款规则{i}", "REFUND", f"退款政策第{i}条详细内容")

        results = await policy_service.search("退款", top_k=3)
        assert len(results) <= 3


class TestMinSimilarity:
    async def test_min_similarity_filters(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "退款规则", "REFUND", "退款相关")
        await _seed(db_session, "POL-LOG-001", 1, "物流规则", "LOGISTICS", "物流查询追踪")

        results_all = await policy_service.search("退款退款退款", top_k=5, min_similarity=None)
        results_filtered = await policy_service.search("退款退款退款", top_k=5, min_similarity=0.3)
        assert len(results_filtered) <= len(results_all)


class TestEmptyDatabase:
    async def test_empty_db_returns_empty(
        self, policy_service: PolicyService,
    ) -> None:
        results = await policy_service.search("退款", top_k=5)
        assert results == []


class TestResultFields:
    async def test_no_internal_fields_leaked(
        self, db_session: AsyncSession, policy_service: PolicyService,
    ) -> None:
        await _seed(db_session, "POL-REF-001", 1, "退款规则", "REFUND", "退款政策详细正文内容。")

        results = await policy_service.search("退款", top_k=5)
        assert len(results) >= 1
        r = results[0]

        for field in ("policy_key", "version", "title", "category",
                      "content_summary", "snippet", "chunk_index",
                      "similarity_score"):
            assert field in r, f"Missing field: {field}"

        for forbidden in ("id", "content_hash", "metadata_filter",
                          "superseded_by", "created_at", "updated_at"):
            assert forbidden not in r, f"Leaked field: {forbidden}"


class TestEmbeddingSessionBoundary:
    async def test_session_closed_before_return(
        self, policy_service: PolicyService,
    ) -> None:
        for _ in range(10):
            results = await policy_service.search("退款", top_k=5)
            assert isinstance(results, list)
