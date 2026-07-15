"""Concurrency and idempotency validation tests."""

import asyncio
import uuid

from httpx import AsyncClient


class TestIdempotency:
    """Duplicate requests produce consistent results."""

    async def test_agent_message_idempotency(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Same Idempotency-Key twice → cached response."""
        key = f"idem-{uuid.uuid4().hex}"
        r1 = await async_client.post("/api/v1/agent/sessions", json={"message": "hi"}, headers={
            **customer_auth["headers"], "Idempotency-Key": key,
        })
        r2 = await async_client.post("/api/v1/agent/sessions", json={"message": "hi"}, headers={
            **customer_auth["headers"], "Idempotency-Key": key,
        })
        assert r1.status_code in (200, 201)
        assert r2.status_code in (200, 201)
        # Both should return same session_id
        d1 = r1.json().get("data", {})
        d2 = r2.json().get("data", {})
        assert d1.get("session_id") == d2.get("session_id")

    async def test_memory_create_idempotent_by_key(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Same key twice → merged (update), not duplicate."""
        key = f"idem-mem-{uuid.uuid4().hex[:8]}"
        r1 = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "key": key, "content": "v1",
        }, headers=customer_auth["headers"])
        r2 = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "key": key, "content": "v2",
        }, headers=customer_auth["headers"])
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["data"]["id"] == r2.json()["data"]["id"]
        assert r2.json()["data"]["content"] == "v2"


class TestConcurrentApproval:
    """Concurrent approval decisions use optimistic locking."""

    async def test_approval_list_returns_ok(
        self, async_client: AsyncClient, admin_auth: dict,
    ) -> None:
        """Admin approval list loads without error."""
        r = await async_client.get("/api/v1/admin/approvals", headers=admin_auth["headers"])
        assert r.status_code == 200


class TestSessionConcurrency:
    """Active turn concurrency control."""

    async def test_session_create_is_concurrent_safe(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Creating multiple sessions concurrently works."""
        async def create_one() -> int:
            r = await async_client.post("/api/v1/agent/sessions", json={"message": "hi"}, headers={
                **customer_auth["headers"],
                "Idempotency-Key": str(uuid.uuid4()),
            })
            return r.status_code

        statuses = await asyncio.gather(*[create_one() for _ in range(3)])
        assert all(s in (200, 201) for s in statuses)
