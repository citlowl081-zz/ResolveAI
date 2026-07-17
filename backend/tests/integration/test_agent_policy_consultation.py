"""End-to-end regression coverage for grounded policy consultations."""

import json
import uuid
from datetime import date
from typing import Any

from httpx import AsyncClient
from sqlalchemy import text

import app.api.v1.agent as agent_module
from app.agent.graph import build_agent_graph
from app.agent.orchestrator import AgentOrchestrator
from app.database.session import _get_session_factory
from app.llm.mock_provider import MockProvider
from app.llm.provider import ChatResponse
from app.rag.embeddings import build_embedding_provider
from app.services.policy_service import PolicyService


def _response(payload: dict[str, Any]) -> ChatResponse:
    return ChatResponse(content=json.dumps(payload, ensure_ascii=False), model="mock")


async def test_headphone_consultation_searches_policy_without_writing(
    async_client: AsyncClient, customer_auth: dict, monkeypatch: Any,
) -> None:
    factory = _get_session_factory()
    policy_key = "POL-RET-997"
    async with factory() as session:
        await session.execute(
            text("DELETE FROM policy_chunks WHERE policy_document_id IN "
                 "(SELECT id FROM policy_documents WHERE policy_key=:key)"),
            {"key": policy_key},
        )
        await session.execute(
            text("DELETE FROM policy_documents WHERE policy_key=:key"),
            {"key": policy_key},
        )
        await session.commit()

    service = PolicyService(factory, build_embedding_provider())
    await service.create_policy(
        policy_key=policy_key,
        title="耳机拆封试用与七日无理由退货规则",
        category="RETURN",
        content=(
            "耳机拆封后，合理试用且商品功能、外观、配件和包装保持完好的，"
            "可按商品页面公示规则申请七日无理由退货；影响二次销售的除外。"
        ),
        content_summary="耳机拆封后的合理试用与商品完好判定。",
        effective_date=date.today(),
        source="company_policy",
        status="ACTIVE",
    )

    provider = MockProvider(responses=[
        _response({
            "intent": "OTHER", "confidence": 0.98,
            "request_mode": "CONSULTATION", "extracted_entities": {},
        }),
        _response({
            "response": "耳机拆封不当然排除退货，需结合合理试用和商品完好情况判断。",
            "propose_action": None,
        }),
        _response({
            "intent": "OTHER", "confidence": 0.98,
            "request_mode": "CONSULTATION", "extracted_entities": {},
        }),
        _response({
            "response": "重复咨询仍只回答政策，不创建工单。",
            "propose_action": None,
        }),
    ])

    def _orchestrator() -> AgentOrchestrator:
        return AgentOrchestrator(
            session_factory=_get_session_factory(),
            graph=build_agent_graph(),  # type: ignore[no-untyped-call]
            llm=provider,
        )

    monkeypatch.setattr(agent_module, "_get_orchestrator", _orchestrator)

    try:
        before = await async_client.get(
            "/api/v1/after-sales/tickets", headers=customer_auth["headers"],
        )
        before_total = before.json()["data"]["total"]

        response = await async_client.post(
            "/api/v1/agent/sessions",
            json={"message": "我买的耳机拆封试用后不合适，还可以七天无理由退货吗？"},
            headers={
                **customer_auth["headers"],
                "Idempotency-Key": f"policy-{uuid.uuid4().hex}",
            },
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert "合理试用" in data["message"]
        assert data["proposed_actions"] == []
        assert any(c["policy_key"] == policy_key for c in data["citations"])

        repeated = await async_client.post(
            f"/api/v1/agent/sessions/{data['session_id']}/messages",
            json={"message": "我再问一次，耳机拆封试用后能退吗？"},
            headers={
                **customer_auth["headers"],
                "Idempotency-Key": f"policy-repeat-{uuid.uuid4().hex}",
            },
        )
        assert repeated.status_code == 200
        repeated_data = repeated.json()["data"]
        assert repeated_data["proposed_actions"] == []
        assert any(c["policy_key"] == policy_key for c in repeated_data["citations"])

        after = await async_client.get(
            "/api/v1/after-sales/tickets", headers=customer_auth["headers"],
        )
        assert after.json()["data"]["total"] == before_total

        async with factory() as session:
            tool_names = await session.execute(text(
                "SELECT tool_name FROM agent_tool_logs "
                "WHERE session_id=:session_id ORDER BY created_at"
            ), {"session_id": data["session_id"]})
            assert tool_names.scalars().all() == [
                "search_after_sales_policy",
                "search_after_sales_policy",
            ]
            trace_rows = await session.execute(text(
                "SELECT node_name, llm_call, tool_calls_summary FROM agent_traces "
                "WHERE session_id=:session_id ORDER BY created_at, sequence"
            ), {"session_id": data["session_id"]})
            traces = trace_rows.mappings().all()
            classify_calls = [
                row["llm_call"] for row in traces
                if row["node_name"] == "classify_intent"
            ]
            assert classify_calls
            assert all(call["provider"] == "mock" for call in classify_calls)
            assert all(call["real_llm_success"] is False for call in classify_calls)
            assert all(call["fallback_used"] is False for call in classify_calls)
            execute_summaries = [
                row["tool_calls_summary"] for row in traces
                if row["node_name"] == "execute_tool"
            ]
            assert execute_summaries
            assert all(summary == [{
                "selected_tool": "search_after_sales_policy",
                "policy_search_executed": True,
            }] for summary in execute_summaries)
    finally:
        async with factory() as session:
            await session.execute(
                text("DELETE FROM policy_chunks WHERE policy_document_id IN "
                     "(SELECT id FROM policy_documents WHERE policy_key=:key)"),
                {"key": policy_key},
            )
            await session.execute(
                text("DELETE FROM policy_documents WHERE policy_key=:key"),
                {"key": policy_key},
            )
            await session.commit()
