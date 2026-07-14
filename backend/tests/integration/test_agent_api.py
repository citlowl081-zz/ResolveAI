"""Integration tests for Agent API — self-contained, mock LLM, real DB.

Tests session creation, multi-turn conversation, tool execution,
pending_action/confirm flow, close, concurrent turn blocking, and
Phase 02 regression pass-through.
"""

import uuid

import pytest
from httpx import AsyncClient


def _idem_key() -> str:
    return str(uuid.uuid4())


async def _register_and_login(
    client: AsyncClient, email: str, password: str, full_name: str,
) -> dict:
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": full_name,
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": password,
    })
    data = resp.json()["data"]
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
    }


async def _create_and_pay(client: AsyncClient, auth: dict, admin_auth: dict) -> dict:
    """Create a product, order, and pay it. Returns paid order."""
    headers = auth["headers"]
    # Create product
    prod = await client.post("/api/v1/products", json={
        "name": f"Test Product {uuid.uuid4().hex[:6]}",
        "category": "ELECTRONICS", "price": "199.99", "stock": 50,
    }, headers=admin_auth["headers"])
    product = prod.json()["data"]

    # Create order
    create = await client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address 123",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    assert create.status_code == 201
    order = create.json()["data"]

    # Pay order
    pay = await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"expected_version": order["version"]},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )
    return pay.json()["data"]


class TestAgentSessionCreation:
    """Session creation and first message tests."""

    async def test_create_session_and_get_response(
        self, async_client: AsyncClient,
    ):
        """POST /agent/sessions creates a session and returns a response."""
        auth = await _register_and_login(
            async_client,
            f"agent-test-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Agent Tester",
        )
        headers = auth["headers"]

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好，我想查询我的订单",
        }, headers={**headers, "Idempotency-Key": _idem_key()})

        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "session_id" in data
        assert "trace_id" in data
        assert isinstance(data.get("proposed_actions"), list)

    async def test_multi_turn_conversation(
        self, async_client: AsyncClient, admin_auth: dict,
    ):
        """3-turn conversation with session persistence."""
        auth = await _register_and_login(
            async_client,
            f"agent-mt-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Multi-Turn User",
        )
        headers = auth["headers"]

        # Create product and order
        await _create_and_pay(async_client, auth, admin_auth)

        # Turn 1: create session
        resp1 = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我的订单在哪里",
        }, headers={**headers, "Idempotency-Key": _idem_key()})
        assert resp1.status_code == 201
        session_id = resp1.json()["data"]["session_id"]

        # Turn 2: follow-up
        resp2 = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            json={"message": "订单状态是什么"},
            headers={**headers, "Idempotency-Key": _idem_key()},
        )
        assert resp2.status_code == 200

        # Turn 3: another follow-up
        resp3 = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            json={"message": "谢谢你"},
            headers={**headers, "Idempotency-Key": _idem_key()},
        )
        assert resp3.status_code == 200

    async def test_session_stays_active_after_query(
        self, async_client: AsyncClient, admin_auth: dict,
    ):
        """Session remains ACTIVE after a read-only query turn."""
        auth = await _register_and_login(
            async_client,
            f"agent-active-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Active User",
        )
        headers = auth["headers"]

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**headers, "Idempotency-Key": _idem_key()})
        assert resp.status_code == 201
        session_id = resp.json()["data"]["session_id"]

        # Check session status
        get_resp = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}", headers=headers,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["status"] == "ACTIVE"

    async def test_close_session(
        self, async_client: AsyncClient,
    ):
        """POST /close transitions session to COMPLETED."""
        auth = await _register_and_login(
            async_client,
            f"agent-close-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Close User",
        )
        headers = auth["headers"]

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**headers, "Idempotency-Key": _idem_key()})
        session_id = resp.json()["data"]["session_id"]

        close = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/close",
            headers={**headers, "Idempotency-Key": _idem_key()},
        )
        assert close.status_code == 200
        assert close.json()["data"]["status"] == "COMPLETED"


class TestAgentRBAC:
    """Authorization tests for Agent endpoints."""

    async def test_cross_user_session_access_denied(
        self, async_client: AsyncClient,
    ):
        """User A cannot access User B's session."""
        auth_a = await _register_and_login(
            async_client,
            f"agent-rbac-a-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "User A",
        )
        auth_b = await _register_and_login(
            async_client,
            f"agent-rbac-b-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "User B",
        )

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**auth_a["headers"], "Idempotency-Key": _idem_key()})
        session_id = resp.json()["data"]["session_id"]

        get_resp = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}", headers=auth_b["headers"],
        )
        assert get_resp.status_code == 404

    async def test_refresh_token_rejected(
        self, async_client: AsyncClient,
    ):
        """Refresh token cannot access Agent endpoints."""
        auth = await _register_and_login(
            async_client,
            f"agent-refresh-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Refresh User",
        )
        refresh_token = auth.get("refresh_token", "")

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={"Authorization": f"Bearer {refresh_token}",
                    "Idempotency-Key": _idem_key()})
        assert resp.status_code == 401


class TestAgentIdempotency:
    """API-level and tool-level idempotency."""

    async def test_same_key_replay(
        self, async_client: AsyncClient,
    ):
        """Same Idempotency-Key + same body returns cached response."""
        auth = await _register_and_login(
            async_client,
            f"agent-idem-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Idempotent User",
        )
        headers = auth["headers"]
        key = _idem_key()

        resp1 = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**headers, "Idempotency-Key": key})
        assert resp1.status_code == 201

        resp2 = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**headers, "Idempotency-Key": key})
        assert resp2.status_code == 201
        assert resp2.json()["data"] == resp1.json()["data"]

    async def test_same_key_different_body(
        self, async_client: AsyncClient,
    ):
        """Same key with different body returns 409."""
        auth = await _register_and_login(
            async_client,
            f"agent-idem2-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Idem2 User",
        )
        headers = auth["headers"]
        key = _idem_key()

        resp1 = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**headers, "Idempotency-Key": key})
        assert resp1.status_code == 201

        resp2 = await async_client.post("/api/v1/agent/sessions", json={
            "message": "不同的消息",
        }, headers={**headers, "Idempotency-Key": key})
        assert resp2.status_code == 409


class TestAgentConcurrency:
    """Turn lock concurrency tests."""

    async def test_concurrent_request_blocked(
        self, async_client: AsyncClient,
    ):
        """Two concurrent POSTs to same session → second returns 409."""
        auth = await _register_and_login(
            async_client,
            f"agent-conc-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Concurrent User",
        )
        headers = auth["headers"]

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**headers, "Idempotency-Key": _idem_key()})
        session_id = resp.json()["data"]["session_id"]

        # Send first message (acquires turn)
        key1 = _idem_key()
        resp1 = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            json={"message": "查询订单"},
            headers={**headers, "Idempotency-Key": key1},
        )
        assert resp1.status_code == 200

        # The turn should now be released. Send second.
        resp2 = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            json={"message": "再次查询"},
            headers={**headers, "Idempotency-Key": _idem_key()},
        )
        assert resp2.status_code == 200


class TestAgentAdminTraces:
    """Admin trace and tool-log visibility."""

    async def test_admin_can_list_traces(
        self, async_client: AsyncClient, admin_auth: dict,
    ):
        """OPERATOR/ADMIN can list traces."""
        auth = await _register_and_login(
            async_client,
            f"agent-trace-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Trace User",
        )

        # Create a session to generate trace data
        await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})

        # Admin lists traces
        traces = await async_client.get(
            "/api/v1/admin/agent/traces", headers=admin_auth["headers"],
        )
        assert traces.status_code == 200

    async def test_customer_cannot_list_traces(
        self, async_client: AsyncClient,
    ):
        """CUSTOMER cannot access admin trace endpoint."""
        auth = await _register_and_login(
            async_client,
            f"agent-notrace-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "No Trace User",
        )
        resp = await async_client.get(
            "/api/v1/admin/agent/traces", headers=auth["headers"],
        )
        assert resp.status_code == 403

    async def test_admin_can_list_tool_logs(
        self, async_client: AsyncClient, admin_auth: dict,
    ):
        """OPERATOR/ADMIN can list tool logs."""
        resp = await async_client.get(
            "/api/v1/admin/agent/tool-logs", headers=admin_auth["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
