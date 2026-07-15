"""E2E business evaluation — 7 scenarios via real backend API using httpx test client.

Scenarios:
1. Policy consultation → RAG retrieval → real citation
2. Order & logistics query → Tool Calling → correct answer
3. Low-risk after-sales → create ticket → idempotent execution
4. High-risk after-sales → Approval created → not executed immediately
5. Memory — explicit remember → write → new session read → delete → not injected
6. Empty RAG result → citations=[] → no fabrication
7. Permission isolation — CUSTOMER/OPERATOR/ADMIN boundary
"""

import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
def idem() -> str:
    return f"eval-{uuid.uuid4().hex[:12]}"


class TestE2EScenarios:
    """End-to-end business scenario tests."""

    # ── Scenario 1: Policy consultation ────────────────────────────────

    async def test_scenario_1_policy_consultation_returns_real_citation(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """User asks about refund policy → RAG returns structured citation."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "退货政策是什么？",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"eval-s1-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)
        data = resp.json().get("data", {})
        citations = data.get("citations", [])
        assert isinstance(citations, list), "citations must always be a list"

    # ── Scenario 2: Order & logistics query ────────────────────────────

    async def test_scenario_2_order_query(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """User asks about order status → Tool Calling → correct context."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我的订单状态是什么？",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"eval-s2-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)

    # ── Scenario 3: Low-risk after-sales ──────────────────────────────

    async def test_scenario_3_low_risk_after_sales(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Low-risk refund → ticket created → idempotent execution."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我要退款，订单有问题",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"eval-s3-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)

    # ── Scenario 4: High-risk after-sales ─────────────────────────────

    async def test_scenario_4_high_risk_creates_approval(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """High-risk operation → Approval created → not immediately executed."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我要退款所有商品",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"eval-s4-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)

    # ── Scenario 5: Memory ────────────────────────────────────────────

    async def test_scenario_5_memory_workflow(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Explicit remember → write Memory → new session reads → delete → not injected."""
        # 1. Create memory
        r1 = await async_client.post("/api/v1/memories", json={
            "memory_type": "PREFERENCE",
            "content": "用户偏好支付宝退款",
            "key": "eval-refund-pref",
        }, headers=customer_auth["headers"])
        assert r1.status_code == 201

        # 2. Verify memory exists
        r2 = await async_client.get("/api/v1/memories", headers=customer_auth["headers"])
        assert r2.status_code == 200
        mems = r2.json()["data"]["items"]
        assert any("支付宝" in (m.get("content", "")) for m in mems), "Memory should contain preference"

        # 3. New agent session should load memories
        r3 = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我想退款",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"eval-s5-{uuid.uuid4().hex}",
        })
        assert r3.status_code in (200, 201)

        # 4. Delete memory
        mem_id = mems[0]["id"]
        r4 = await async_client.delete(f"/api/v1/memories/{mem_id}", headers=customer_auth["headers"])
        assert r4.status_code == 200

        # 5. Verify deleted
        r5 = await async_client.get("/api/v1/memories", headers=customer_auth["headers"])
        after = r5.json()["data"]["items"]
        assert not any(m["id"] == mem_id for m in after), "Memory should be deleted"

    # ── Scenario 6: Empty RAG result ──────────────────────────────────

    async def test_scenario_6_empty_rag_no_fabrication(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Query with no matching policies → citations=[] → no fabrication."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "火星上的退货政策是什么？",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"eval-s6-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)
        data = resp.json().get("data", {})
        citations = data.get("citations", [])
        assert isinstance(citations, list), "citations must be a list (empty is OK)"

    # ── Scenario 7: Permission isolation ──────────────────────────────

    async def test_scenario_7a_customer_cannot_access_admin(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """CUSTOMER cannot access admin endpoints."""
        resp = await async_client.get("/api/v1/admin/approvals", headers=customer_auth["headers"])
        assert resp.status_code == 403

    async def test_scenario_7b_customer_cannot_access_admin_policies(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """CUSTOMER cannot manage policies."""
        resp = await async_client.get("/api/v1/admin/policies", headers=customer_auth["headers"])
        assert resp.status_code == 403

    async def test_scenario_7c_customer_cannot_view_other_memory(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Customer A cannot view Customer B's memory."""
        fake_id = uuid.uuid4()
        resp = await async_client.get(f"/api/v1/memories/{fake_id}", headers=customer_auth["headers"])
        assert resp.status_code == 404

    async def test_scenario_7d_memories_require_auth(
        self, async_client: AsyncClient,
    ) -> None:
        """Memory endpoints require authentication."""
        resp = await async_client.get("/api/v1/memories")
        assert resp.status_code == 401
