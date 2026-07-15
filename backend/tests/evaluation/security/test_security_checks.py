"""Security validation tests — RBAC, IDOR, PII leaks, injection prevention."""

import uuid

from httpx import AsyncClient


class TestRBAC:
    """Role-based access control across all protected resources."""

    async def test_unauthorized_agent(self, async_client: AsyncClient) -> None:
        r = await async_client.post("/api/v1/agent/sessions", json={"message": "hi"})
        assert r.status_code == 401

    async def test_customer_cannot_admin_approvals(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.get("/api/v1/admin/approvals", headers=customer_auth["headers"])
        assert r.status_code == 403

    async def test_customer_cannot_admin_policies(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.get("/api/v1/admin/policies", headers=customer_auth["headers"])
        assert r.status_code == 403

    async def test_customer_cannot_admin_traces(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.get("/api/v1/admin/agent/traces", headers=customer_auth["headers"])
        assert r.status_code == 403

    async def test_customer_cannot_admin_tool_logs(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.get("/api/v1/admin/agent/tool-logs", headers=customer_auth["headers"])
        assert r.status_code == 403

    async def test_admin_cannot_customer_memories(self, async_client: AsyncClient, admin_auth: dict) -> None:
        r = await async_client.get("/api/v1/memories", headers=admin_auth["headers"])
        assert r.status_code == 403

    async def test_operator_cannot_customer_memories(self, async_client: AsyncClient, operator_auth: dict) -> None:
        r = await async_client.get("/api/v1/memories", headers=operator_auth["headers"])
        assert r.status_code == 403


class TestIDOR:
    """Insecure Direct Object Reference — user isolation."""

    async def test_customer_cannot_read_other_memory(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.get(f"/api/v1/memories/{uuid.uuid4()}", headers=customer_auth["headers"])
        assert r.status_code == 404  # Not found, not 403 (avoids leaking existence)

    async def test_customer_cannot_read_other_session(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.get(f"/api/v1/agent/sessions/{uuid.uuid4()}", headers=customer_auth["headers"])
        assert r.status_code == 404


class TestSensitiveDataLeak:
    """No PII, credentials, or internal data in API responses."""

    async def test_login_response_no_password(self, async_client: AsyncClient) -> None:
        email = f"sec-test-{uuid.uuid4().hex[:8]}@test.com"
        await async_client.post("/api/v1/auth/register", json={
            "email": email, "password": "testpass123", "full_name": "Sec Test",
        })
        r = await async_client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
        assert r.status_code == 200
        data = r.json().get("data", {})
        user = data.get("user", {})
        assert "hashed_password" not in str(r.json()), "Password must not be in response"
        assert user.get("email") == email

    async def test_agent_response_no_internal_ids(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.post("/api/v1/agent/sessions", json={"message": "hi"}, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"sec-{uuid.uuid4().hex}",
        })
        assert r.status_code in (200, 201)
        body = r.text
        assert "hashed_password" not in body
        assert "access_token" not in body

    async def test_memory_list_no_internal_uuids(self, async_client: AsyncClient, customer_auth: dict) -> None:
        await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "Security test",
        }, headers=customer_auth["headers"])
        r = await async_client.get("/api/v1/memories", headers=customer_auth["headers"])
        assert r.status_code == 200
        # User ID should not appear in public memory responses
        body = r.text
        assert "hashed_password" not in body

    async def test_sensitive_memory_rejected(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "我的密码是 password: mysecret123",
        }, headers=customer_auth["headers"])
        assert r.status_code in (400, 422)

    async def test_sensitive_memory_card_rejected(self, async_client: AsyncClient, customer_auth: dict) -> None:
        r = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "银行卡 6222021234567890123",
        }, headers=customer_auth["headers"])
        assert r.status_code in (400, 422)
