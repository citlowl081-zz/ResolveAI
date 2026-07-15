"""Performance and latency validation — baseline response times."""

import time
import uuid

from httpx import AsyncClient


class TestAPILatency:
    """Basic API response time validation (no real LLM calls)."""

    async def test_health_check_latency(self, async_client: AsyncClient) -> None:
        t0 = time.monotonic()
        r = await async_client.get("/health")
        elapsed = (time.monotonic() - t0) * 1000
        assert r.status_code == 200
        assert elapsed < 500, f"Health check too slow: {elapsed:.0f}ms"

    async def test_auth_me_latency(self, async_client: AsyncClient, customer_auth: dict) -> None:
        t0 = time.monotonic()
        r = await async_client.get("/api/v1/auth/me", headers=customer_auth["headers"])
        elapsed = (time.monotonic() - t0) * 1000
        assert r.status_code == 200
        assert elapsed < 1000, f"Auth me too slow: {elapsed:.0f}ms"

    async def test_products_list_latency(self, async_client: AsyncClient, customer_auth: dict) -> None:
        t0 = time.monotonic()
        r = await async_client.get("/api/v1/products", headers=customer_auth["headers"])
        elapsed = (time.monotonic() - t0) * 1000
        assert r.status_code == 200
        assert elapsed < 1000, f"Products list too slow: {elapsed:.0f}ms"

    async def test_orders_list_latency(self, async_client: AsyncClient, customer_auth: dict) -> None:
        t0 = time.monotonic()
        r = await async_client.get("/api/v1/orders", headers=customer_auth["headers"])
        elapsed = (time.monotonic() - t0) * 1000
        assert r.status_code == 200
        assert elapsed < 1000, f"Orders list too slow: {elapsed:.0f}ms"

    async def test_agent_session_create_latency(self, async_client: AsyncClient, customer_auth: dict) -> None:
        t0 = time.monotonic()
        r = await async_client.post("/api/v1/agent/sessions", json={"message": "hi"}, headers={
            **customer_auth["headers"],
            "Idempotency-Key": str(uuid.uuid4()),
        })
        elapsed = (time.monotonic() - t0) * 1000
        assert r.status_code in (200, 201)
        assert elapsed < 5000, f"Agent session create too slow: {elapsed:.0f}ms"


class TestDBConnection:
    """Database connection pool management."""

    async def test_multiple_requests_no_connection_leak(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """20 sequential requests should not exhaust connections."""
        for _ in range(20):
            r = await async_client.get("/api/v1/auth/me", headers=customer_auth["headers"])
            assert r.status_code == 200
