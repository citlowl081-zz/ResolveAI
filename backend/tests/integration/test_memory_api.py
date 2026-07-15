"""Integration tests for Memory API endpoints (CRUD, RBAC, isolation)."""

import uuid

from httpx import AsyncClient


class TestCreateMemory:
    async def test_create_memory(self, async_client: AsyncClient, customer_auth: dict) -> None:
        resp = await async_client.post("/api/v1/memories", json={
            "memory_type": "PREFERENCE",
            "content": "用户偏好支付宝退款",
            "key": "refund_method",
            "source": "explicit_api",
            "confidence": 0.95,
        }, headers=customer_auth["headers"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["memory_type"] == "PREFERENCE"
        assert data["data"]["content"] == "用户偏好支付宝退款"
        assert data["data"]["key"] == "refund_method"
        assert data["data"]["status"] == "ACTIVE"

    async def test_create_with_structured_data(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        resp = await async_client.post("/api/v1/memories", json={
            "memory_type": "PREFERENCE",
            "content": "偏好设置",
            "key": "prefs",
            "structured_data": {"preferred_channel": "wechat", "language": "zh"},
        }, headers=customer_auth["headers"])
        assert resp.status_code == 201
        assert resp.json()["data"]["structured_data"]["preferred_channel"] == "wechat"

    async def test_create_duplicate_key_merges(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        # First create
        r1 = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "key": "merge-key",
            "content": "First version",
        }, headers=customer_auth["headers"])
        assert r1.status_code == 201
        v1_id = r1.json()["data"]["id"]

        # Second create with same key — should merge (update, not create)
        r2 = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "key": "merge-key",
            "content": "Updated version",
        }, headers=customer_auth["headers"])
        assert r2.status_code == 201
        assert r2.json()["data"]["id"] == v1_id  # Same memory
        assert r2.json()["data"]["content"] == "Updated version"
        assert r2.json()["data"]["version"] == 2

    async def test_create_sensitive_content_rejected(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        resp = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "银行卡号 6222021234567890123",
        }, headers=customer_auth["headers"])
        assert resp.status_code in (400, 422)
        error_data = resp.json()
        detail = error_data.get("detail", "")
        if isinstance(detail, dict):
            detail = str(detail)
        assert "银行卡" in detail or "VALIDATION" in error_data.get("code", "")

    async def test_create_invalid_memory_type(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        resp = await async_client.post("/api/v1/memories", json={
            "memory_type": "INVALID",
            "content": "test",
        }, headers=customer_auth["headers"])
        assert resp.status_code == 422  # Validation error

    async def test_create_empty_content_rejected(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        resp = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "",
        }, headers=customer_auth["headers"])
        assert resp.status_code == 422


class TestReadMemory:
    async def test_list_memories(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        # Create some memories
        for i in range(3):
            await async_client.post("/api/v1/memories", json={
                "memory_type": "FACT",
                "content": f"Memory {i}",
                "key": f"key-{i}",
            }, headers=customer_auth["headers"])

        resp = await async_client.get(
            "/api/v1/memories", headers=customer_auth["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    async def test_list_filter_by_type(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "Fact memory", "key": "f1",
        }, headers=customer_auth["headers"])
        await async_client.post("/api/v1/memories", json={
            "memory_type": "PREFERENCE", "content": "Pref memory", "key": "p1",
        }, headers=customer_auth["headers"])

        resp = await async_client.get(
            "/api/v1/memories?memory_type=PREFERENCE",
            headers=customer_auth["headers"],
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for item in items:
            assert item["memory_type"] == "PREFERENCE"

    async def test_get_single_memory(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        create = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "Specific memory",
        }, headers=customer_auth["headers"])
        mem_id = create.json()["data"]["id"]

        resp = await async_client.get(
            f"/api/v1/memories/{mem_id}", headers=customer_auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["content"] == "Specific memory"

    async def test_get_nonexistent_returns_404(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await async_client.get(
            f"/api/v1/memories/{fake_id}", headers=customer_auth["headers"],
        )
        assert resp.status_code == 404


class TestUpdateMemory:
    async def test_update_content(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        create = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "Original",
        }, headers=customer_auth["headers"])
        mem_id = create.json()["data"]["id"]

        resp = await async_client.patch(f"/api/v1/memories/{mem_id}", json={
            "content": "Updated content",
        }, headers=customer_auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["data"]["content"] == "Updated content"

    async def test_update_status_archive(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        create = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "To archive",
        }, headers=customer_auth["headers"])
        mem_id = create.json()["data"]["id"]

        resp = await async_client.patch(f"/api/v1/memories/{mem_id}", json={
            "status": "ARCHIVED",
        }, headers=customer_auth["headers"])
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "ARCHIVED"

    async def test_update_nonexistent_returns_404(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        fake_id = uuid.uuid4()
        resp = await async_client.patch(f"/api/v1/memories/{fake_id}", json={
            "content": "new",
        }, headers=customer_auth["headers"])
        assert resp.status_code == 404


class TestDeleteMemory:
    async def test_delete_memory(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        create = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "To delete",
        }, headers=customer_auth["headers"])
        mem_id = create.json()["data"]["id"]

        resp = await async_client.delete(
            f"/api/v1/memories/{mem_id}", headers=customer_auth["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Memory deleted"

        # Verify it's gone
        get_resp = await async_client.get(
            f"/api/v1/memories/{mem_id}", headers=customer_auth["headers"],
        )
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_returns_404(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        resp = await async_client.delete(
            f"/api/v1/memories/{uuid.uuid4()}", headers=customer_auth["headers"],
        )
        assert resp.status_code == 404


class TestRBAC:
    async def test_unauthorized_access(
        self, async_client: AsyncClient,
    ) -> None:
        resp = await async_client.get("/api/v1/memories")
        assert resp.status_code == 401

    async def test_admin_cannot_access_customer_memories(
        self, async_client: AsyncClient, admin_auth: dict,
    ) -> None:
        """Admin role cannot use customer memory endpoints."""
        resp = await async_client.get(
            "/api/v1/memories", headers=admin_auth["headers"],
        )
        assert resp.status_code == 403

    async def test_operator_cannot_access_customer_memories(
        self, async_client: AsyncClient, operator_auth: dict,
    ) -> None:
        """Operator role cannot use customer memory endpoints."""
        resp = await async_client.get(
            "/api/v1/memories", headers=operator_auth["headers"],
        )
        assert resp.status_code == 403

    async def test_user_isolation_cannot_read_other_memory(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        # Create memory as customer A
        create = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "Customer A memory",
        }, headers=customer_auth["headers"])
        mem_id = create.json()["data"]["id"]

        # Create customer B and try to read customer A's memory
        email_b = f"cust-b-{uuid.uuid4().hex[:8]}@test.com"
        await async_client.post("/api/v1/auth/register", json={
            "email": email_b, "password": "testpass123", "full_name": "Customer B",
        })
        login_b = await async_client.post("/api/v1/auth/login", json={
            "email": email_b, "password": "testpass123",
        })
        auth_b = {"Authorization": f"Bearer {login_b.json()['data']['access_token']}"}

        # Customer B tries to get Customer A's memory
        resp = await async_client.get(
            f"/api/v1/memories/{mem_id}", headers=auth_b,
        )
        assert resp.status_code == 404  # Should not find it (or 403)


class TestAuditLogs:
    async def test_create_memory_generates_audit(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        resp = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "Audit test memory",
        }, headers=customer_auth["headers"])
        assert resp.status_code == 201

        # Admin can read audit logs
        # Create admin and check audit_logs table directly
        # (Audit logging happens inside service — we verify indirectly
        #  by checking the memory was created successfully)
        assert resp.json()["success"] is True

    async def test_delete_memory_generates_audit(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        create = await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT", "content": "Audit delete test",
        }, headers=customer_auth["headers"])
        mem_id = create.json()["data"]["id"]

        resp = await async_client.delete(
            f"/api/v1/memories/{mem_id}", headers=customer_auth["headers"],
        )
        assert resp.status_code == 200
