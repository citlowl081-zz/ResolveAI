"""RAG evaluation metrics — HitRate@5, Precision@1, MRR, Fabrication check."""

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings
from app.rag.embeddings import build_embedding_provider
from app.services.policy_service import PolicyService

_EVAL_PATH = Path(__file__).parent / "eval_queries.json"


def _load_queries() -> list[dict]:
    with open(_EVAL_PATH) as f:
        return json.load(f)  # type: ignore[no-any-return]


def _hit_rate_at_k(retrieved: list[str], expected: list[str], k: int = 5) -> float:
    top = retrieved[:k]
    return 1.0 if any(k in expected for k in top) else 0.0


def _precision_at_1(retrieved: list[str], expected: list[str]) -> float:
    return 1.0 if retrieved and retrieved[0] in expected else 0.0


def _mrr(retrieved: list[str], expected: list[str]) -> float:
    for i, key in enumerate(retrieved, start=1):
        if key in expected:
            return 1.0 / i
    return 0.0


def _fabrication_rate(retrieved: list[str]) -> float:
    """Fraction of results with empty/placeholder policy_keys (fabricated)."""
    if not retrieved:
        return 0.0
    n = len(retrieved)
    fabrications = sum(1 for k in retrieved if not k or k == "")
    return fabrications / n


async def _run_eval() -> dict:
    engine = create_async_engine(
        settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    provider = build_embedding_provider()
    svc = PolicyService(session_factory=factory, embedding_provider=provider)

    queries = _load_queries()
    hit5_sum = 0.0
    p1_sum = 0.0
    mrr_sum = 0.0
    fab_sum = 0.0
    n = len(queries)

    for q in queries:
        results = await svc.search(q["query"], top_k=5)
        keys = [r["policy_key"] for r in results]
        expected = q["expected"]
        hit5_sum += _hit_rate_at_k(keys, expected)
        p1_sum += _precision_at_1(keys, expected)
        mrr_sum += _mrr(keys, expected)
        fab_sum += _fabrication_rate(keys)

    await engine.dispose()
    return {
        "hit_rate_at_5": round(hit5_sum / n, 4) if n else 0.0,
        "precision_at_1": round(p1_sum / n, 4) if n else 0.0,
        "mrr": round(mrr_sum / n, 4) if n else 0.0,
        "fabrication_rate": round(fab_sum / n, 4) if n else 0.0,
        "total_queries": n,
    }


class TestRAGMetrics:
    """HitRate@5, Precision@1, MRR, and Fabrication check across 21 queries."""

    async def _ensure_ingested(self) -> None:
        engine = create_async_engine(
            settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from pathlib import Path as P

        from app.rag.ingestion import PolicyIngestionService
        policies_dir = P(__file__).resolve().parents[4] / "data" / "policies"
        provider = build_embedding_provider()
        ingester = PolicyIngestionService(
            session_factory=factory, embedding_provider=provider, policies_dir=policies_dir,
        )
        await ingester.ingest_all(activate=True)
        await engine.dispose()

    async def test_hit_rate_at_5_gte_85(self) -> None:
        """HitRate@5 must be >= 0.85 — at most 3 misses out of 21."""
        await self._ensure_ingested()
        metrics = await _run_eval()
        assert metrics["hit_rate_at_5"] >= 0.85, (
            f"HitRate@5={metrics['hit_rate_at_5']} below 0.85 threshold"
        )

    async def test_precision_at_1_gte_50(self) -> None:
        """Precision@1 must be >= 0.50 — top result correct at least half the time."""
        await self._ensure_ingested()
        metrics = await _run_eval()
        assert metrics["precision_at_1"] >= 0.50, (
            f"Precision@1={metrics['precision_at_1']} below 0.50 threshold"
        )

    async def test_mrr_gte_60(self) -> None:
        """MRR must be >= 0.60 — first correct result ranks high on average."""
        await self._ensure_ingested()
        metrics = await _run_eval()
        assert metrics["mrr"] >= 0.60, (
            f"MRR={metrics['mrr']} below 0.60 threshold"
        )

    async def test_fabrication_rate_zero(self) -> None:
        """No fabricated (empty) policy_keys in any result set."""
        await self._ensure_ingested()
        metrics = await _run_eval()
        assert metrics["fabrication_rate"] == 0.0, (
            f"Fabrication rate={metrics['fabrication_rate']} — some results have empty policy_keys"
        )
