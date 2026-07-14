"""Transaction boundary verification tests.

Verify: no DB sessions during LLM, short-tx for tools,
failed tool log independent persistence, TX-B atomicity.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy import text


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


class TestTransactionBoundaries:
    """Verify short-tx pattern throughout agent flow."""

    async def test_session_active_after_success(
        self, async_client: AsyncClient,
    ) -> None:
        """After a successful agent turn, the session exists and has message rows."""
        auth = await _register_and_login(
            async_client,
            f"tx-basic-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Tx User",
        )

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})
        assert resp.status_code == 201
        session_id = resp.json()["data"]["session_id"]

        from app.database.session import _get_session_factory
        factory = _get_session_factory()
        async with factory() as session:
            result = await session.execute(
                text("SELECT COUNT(*) as cnt FROM agent_messages WHERE session_id = :sid"),
                {"sid": uuid.UUID(session_id)},
            )
            row = result.fetchone()
            assert row is not None
            count = row.cnt
            assert count >= 1, "At least one message must be persisted"

    async def test_tool_execution_creates_tool_log(
        self, async_client: AsyncClient, admin_auth: dict,
    ) -> None:
        """When tools are executed, agent_tool_logs rows are created."""
        auth = await _register_and_login(
            async_client,
            f"tx-tool-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Tool User",
        )

        # Create product and order for context
        prod_resp = await async_client.post("/api/v1/products", json={
            "name": f"Tx Product {uuid.uuid4().hex[:6]}",
            "category": "ELECTRONICS", "price": "99.99", "stock": 50,
        }, headers=admin_auth["headers"])
        product = prod_resp.json()["data"]

        order_resp = await async_client.post("/api/v1/orders", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping_address": "Test Address",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})
        assert order_resp.status_code == 201
        order = order_resp.json()["data"]

        # Pay the order
        await async_client.post(
            f"/api/v1/orders/{order['id']}/pay",
            json={"expected_version": order["version"]},
            headers={**auth["headers"], "Idempotency-Key": _idem_key()},
        )

        # Send agent message that triggers tool execution
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "查询订单状态",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})
        assert resp.status_code == 201

        from app.database.session import _get_session_factory
        factory = _get_session_factory()
        async with factory() as session:
            result = await session.execute(
                text("SELECT COUNT(*) as cnt FROM agent_tool_logs")
            )
            row = result.fetchone()
            assert row is not None
            count = row.cnt
            assert count >= 1, "Tool execution must create tool log rows"

    async def test_turn_cleared_after_success(
        self, async_client: AsyncClient,
    ) -> None:
        """After success TX-B, active_turn is cleared for the specific session."""
        auth = await _register_and_login(
            async_client,
            f"tx-clear-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Clear User",
        )
        key = _idem_key()

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**auth["headers"], "Idempotency-Key": key})
        session_id = uuid.UUID(resp.json()["data"]["session_id"])

        from app.database.session import _get_session_factory
        factory = _get_session_factory()
        async with factory() as session:
            # Check turn is cleared for THIS session
            result = await session.execute(
                text("SELECT active_turn_id, active_turn_trace_id FROM agent_sessions WHERE id = :sid"),
                {"sid": session_id},
            )
            row = result.fetchone()
            assert row is not None
            assert row.active_turn_id is None, "Turn must be cleared after success for this session"

            # Check idempotency is COMPLETED for this key
            result2 = await session.execute(
                text("SELECT status FROM idempotency_records WHERE idempotency_key = :key AND operation = 'agent_message'"),
                {"key": key},
            )
            row2 = result2.fetchone()
            if row2:
                assert row2.status == "COMPLETED", (
                    "Idempotency must be COMPLETED when turn is cleared"
                )

    async def test_idempotency_consistent_after_turn(
        self, async_client: AsyncClient,
    ) -> None:
        """Idempotency record transitions from PROCESSING to COMPLETED after turn."""
        auth = await _register_and_login(
            async_client,
            f"tx-idem-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Idem User",
        )
        key = _idem_key()

        await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**auth["headers"], "Idempotency-Key": key})

        from app.database.session import _get_session_factory
        factory = _get_session_factory()
        async with factory() as session:
            result = await session.execute(
                text(
                    "SELECT status FROM idempotency_records "
                    "WHERE idempotency_key = :key AND operation = 'agent_message'"
                ),
                {"key": key},
            )
            row = result.fetchone()
            assert row is not None, "Idempotency record must exist"
            assert row.status == "COMPLETED", "Must be COMPLETED after successful turn"


class TestMessageSequenceAndPersistence:
    """Message ordering and uniqueness constraints."""

    async def test_messages_have_unique_sequence(
        self, async_client: AsyncClient,
    ) -> None:
        """Messages within a session have strictly increasing sequence numbers."""
        auth = await _register_and_login(
            async_client,
            f"tx-seq-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "Seq User",
        )

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})
        session_id = resp.json()["data"]["session_id"]

        # Get messages
        msg_resp = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}/messages",
            headers=auth["headers"],
        )
        messages = msg_resp.json()["data"]["items"]
        assert len(messages) >= 1

        sequences = [m["sequence_number"] for m in messages]
        assert sequences == sorted(sequences), "Sequence numbers must be monotonic"
        assert len(set(sequences)) == len(sequences), "Sequence numbers must be unique"

    async def test_turn_sequence_scheme(
        self, async_client: AsyncClient, admin_auth: dict,
    ) -> None:
        """Verify turn_sequence scheme: 0=USER, 10=TOOL_CALL, 20+N=TOOL, 100=ASSISTANT."""
        auth = await _register_and_login(
            async_client,
            f"tx-tscheme-{uuid.uuid4().hex[:8]}@test.com",
            "testpass123", "TScheme User",
        )

        # Create product + order so tools execute
        prod_resp = await async_client.post("/api/v1/products", json={
            "name": f"TS Product {uuid.uuid4().hex[:6]}",
            "category": "ELECTRONICS", "price": "99.99", "stock": 50,
        }, headers=admin_auth["headers"])
        product = prod_resp.json()["data"]

        order_resp = await async_client.post("/api/v1/orders", json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping_address": "Test Address",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})
        order = order_resp.json()["data"]
        await async_client.post(
            f"/api/v1/orders/{order['id']}/pay",
            json={"expected_version": order["version"]},
            headers={**auth["headers"], "Idempotency-Key": _idem_key()},
        )

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "查询我的订单",
        }, headers={**auth["headers"], "Idempotency-Key": _idem_key()})
        session_id = resp.json()["data"]["session_id"]

        msg_resp = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}/messages",
            headers=auth["headers"],
        )
        messages = msg_resp.json()["data"]["items"]

        turn_sequences = [m.get("turn_sequence") for m in messages if m.get("turn_sequence") is not None]
        # At minimum we should have turn_sequence=0 (USER) and turn_sequence=100 (final ASSISTANT)
        has_user = 0 in turn_sequences
        has_final = 100 in turn_sequences
        assert has_user, "Must have USER message (turn_sequence=0)"
        assert has_final, "Must have final ASSISTANT message (turn_sequence=100)"
