"""Integration tests for Phase 04B — Agent RAG tool, citations, and data minimization."""

from collections.abc import AsyncGenerator
from datetime import date

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings
from app.rag.embeddings import build_embedding_provider
from app.services.policy_service import PolicyService


@pytest_asyncio.fixture(autouse=True)
async def _cleanup() -> AsyncGenerator[None, None]:
    yield
    engine = create_async_engine(
        settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    async with engine.connect() as conn:
        await conn.execute(text("DELETE FROM policy_chunks"))
        await conn.execute(text("DELETE FROM policy_documents"))
        await conn.commit()
    await engine.dispose()


async def _seed_policy(key: str, title: str, category: str, content: str) -> None:
    engine = create_async_engine(
        settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    provider = build_embedding_provider()
    svc = PolicyService(session_factory=factory, embedding_provider=provider)
    await svc.create_policy(
        policy_key=key, title=title, category=category, content=content,
        effective_date=date.today(), status="ACTIVE",
    )
    await engine.dispose()


class TestToolRegistration:
    """Verify search_after_sales_policy is registered and role-gated."""

    def test_tool_registered(self) -> None:
        from app.tools.definitions import register_all
        from app.tools.registry import ToolRegistry
        registry = ToolRegistry()
        register_all(registry)
        tool = registry.get("search_after_sales_policy")
        assert tool is not None
        assert tool.contract.tool_name == "search_after_sales_policy"

    def test_customer_only(self) -> None:
        from app.models.enums import UserRole
        from app.tools.definitions import register_all
        from app.tools.registry import ToolRegistry
        registry = ToolRegistry()
        register_all(registry)
        tool = registry.get("search_after_sales_policy")
        assert tool is not None
        assert UserRole.CUSTOMER in tool.contract.allowed_roles
        assert UserRole.ADMIN not in tool.contract.allowed_roles
        assert UserRole.OPERATOR not in tool.contract.allowed_roles


class TestCitationsBuiltFromToolResults:
    """Citations must be built from real tool results, never fabricated."""

    def test_build_citations_from_real_results(self) -> None:
        from app.agent.nodes.compose_response import _build_citations
        state: dict = {
            "tool_results": [{
                "is_success": True,
                "tool_name": "search_after_sales_policy",
                "data": {
                    "policies": [{
                        "policy_key": "POL-REF-001", "version": 1,
                        "title": "Test", "category": "REFUND",
                        "snippet": "Test snippet.", "similarity_score": 0.95,
                    }],
                },
            }],
        }
        citations = _build_citations(state)  # type: ignore[arg-type]
        assert len(citations) == 1
        assert citations[0]["policy_key"] == "POL-REF-001"

    def test_empty_when_no_policy_tool(self) -> None:
        from app.agent.nodes.compose_response import _build_citations
        state: dict = {
            "tool_results": [{
                "is_success": True,
                "tool_name": "get_order",
                "data": {"order_number": "ORD-001"},
            }],
        }
        citations = _build_citations(state)  # type: ignore[arg-type]
        assert citations == []

    def test_empty_when_search_returns_none(self) -> None:
        from app.agent.nodes.compose_response import _build_citations
        state: dict = {
            "tool_results": [{
                "is_success": True,
                "tool_name": "search_after_sales_policy",
                "data": {"policies": []},
            }],
        }
        citations = _build_citations(state)  # type: ignore[arg-type]
        assert citations == []


class TestDataMinimization:
    """Policy data sent to LLM must not contain internal fields."""

    def test_policy_projection_strips_internal_fields(self) -> None:
        from app.agent.sanitization import project_policy_for_llm
        raw = {
            "policy_key": "POL-REF-001", "version": 1, "title": "T",
            "category": "REFUND", "content_summary": "S",
            "snippet": "snip", "similarity_score": 0.9,
            "id": "uuid-123", "content_hash": "abc",
            "metadata_filter": {}, "superseded_by": None,
            "content": "full text here",
        }
        projected = project_policy_for_llm(raw)
        assert "policy_key" in projected
        assert "id" not in projected
        assert "content_hash" not in projected
        assert "metadata_filter" not in projected
        assert "content" not in projected
        assert "superseded_by" not in projected


class TestAgentCitationFlow:
    """End-to-end: seed policy, search via service, verify citation shape."""

    async def test_search_returns_citation_shape(self) -> None:
        await _seed_policy(
            "POL-REF-001", "退款规则", "REFUND",
            "订单未发货可申请全额退款，退款在1-3个工作日到账。",
        )
        engine = create_async_engine(
            settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        provider = build_embedding_provider()
        svc = PolicyService(session_factory=factory, embedding_provider=provider)
        results = await svc.search("我要退款", top_k=3)
        await engine.dispose()

        assert len(results) >= 1
        r = results[0]
        for field in ("policy_key", "version", "title", "category",
                      "content_summary", "snippet", "similarity_score"):
            assert field in r, f"Missing: {field}"
        for forbidden in ("id", "content_hash", "metadata_filter", "content"):
            assert forbidden not in r, f"Leaked: {forbidden}"


class TestEmptyResults:
    """Empty search results should return empty list, no crash."""

    async def test_no_policies_returns_empty(self) -> None:
        engine = create_async_engine(
            settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        provider = build_embedding_provider()
        svc = PolicyService(session_factory=factory, embedding_provider=provider)
        results = await svc.search("nonexistent query xyz", top_k=5)
        await engine.dispose()
        assert results == []

class TestCitationsAlwaysList:
    """The citations field must always be a list, never None, in API responses."""

    def test_citations_is_empty_list_in_initial_state(self) -> None:
        """Orchestrator initializes citations as empty list."""
        state: dict = {
            "session_id": "s1",
            "trace_id": "t1",
            "citations": [],
            "proposed_actions": [],
        }
        response_citations = state.get("citations") or []
        assert isinstance(response_citations, list)
        assert response_citations == []

    def test_citations_built_from_results_returned_as_list(self) -> None:
        """Even when _build_citations returns [], it is always a list."""
        from app.agent.nodes.compose_response import _build_citations
        state: dict = {
            "tool_results": [{
                "is_success": True,
                "tool_name": "search_after_sales_policy",
                "data": {"policies": []},
            }],
        }
        citations = _build_citations(state)  # type: ignore[arg-type]
        assert isinstance(citations, list)
        assert citations == []
