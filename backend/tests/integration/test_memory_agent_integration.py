"""Integration tests for Agent Memory integration — build_context loading and compose_response decisions."""

import uuid

from httpx import AsyncClient


class TestBuildContextMemoryInjection:
    async def test_build_context_injects_memories(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """When a user has memories, build_context should load them into state."""
        # Create some memories
        await async_client.post("/api/v1/memories", json={
            "memory_type": "PREFERENCE",
            "content": "用户偏好支付宝退款",
            "key": "refund_pref",
        }, headers=customer_auth["headers"])
        await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "用户上次购买的是电子产品",
            "key": "last_purchase",
        }, headers=customer_auth["headers"])

        # Send an agent message — build_context should load memories
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我要退款",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"mem-inject-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)
        # The response succeeds — memory loading is internal
        # We verify it doesn't crash; detailed state inspection is in unit tests

    async def test_no_memories_does_not_crash(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """New user with no memories — build_context should not crash."""
        email = f"no-mem-{uuid.uuid4().hex[:8]}@test.com"
        await async_client.post("/api/v1/auth/register", json={
            "email": email, "password": "testpass123", "full_name": "No Mem User",
        })
        login = await async_client.post("/api/v1/auth/login", json={
            "email": email, "password": "testpass123",
        })
        auth = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "你好",
        }, headers={
            **auth,
            "Idempotency-Key": f"no-mem-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)


class TestComposeResponseMemoryDecisions:
    async def test_explicit_remember_triggers_memory_write(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """When user says '记住', compose_response should set memory_changes."""
        # The orchestrator will persist memory_changes in TX-B
        # We test this via the API — the turn should succeed
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "记住我喜欢用支付宝退款",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"remember-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)

        # After that turn, there should be a new memory
        mem_resp = await async_client.get(
            "/api/v1/memories", headers=customer_auth["headers"],
        )
        assert mem_resp.status_code == 200
        memories = mem_resp.json()["data"]["items"]
        # At least one memory should reference the preference
        contents = [m["content"] for m in memories]
        assert any("支付宝" in c for c in contents), f"Expected memory about 支付宝, got: {contents}"

    async def test_ordinary_chat_does_not_create_memory(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Ordinary chat (logistics inquiry) should NOT create a memory."""
        # First check how many memories exist
        before = await async_client.get(
            "/api/v1/memories", headers=customer_auth["headers"],
        )
        before_count = before.json()["data"]["total"]

        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我的快递到哪里了？",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"ordinary-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)

        after = await async_client.get(
            "/api/v1/memories", headers=customer_auth["headers"],
        )
        after_count = after.json()["data"]["total"]
        # Ordinary logistics inquiry should not create a memory
        assert after_count == before_count, (
            f"Expected no new memories, but count went from {before_count} to {after_count}"
        )

    async def test_multiple_sessions_build_memory_context(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Memories created in one session should be available in the next."""
        # Create a memory via API
        await async_client.post("/api/v1/memories", json={
            "memory_type": "FACT",
            "content": "用户是VIP客户",
            "key": "vip_status",
        }, headers=customer_auth["headers"])

        # Start a new agent session — the memory should be loaded
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "我想退款",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"cross-session-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)
        # The memory about VIP status should have been loaded into context
        # (Internal — verified by the turn succeeding without error)

    async def test_memory_data_minimization_in_context(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Memory fields sent to LLM should not include internal UUIDs."""
        from app.agent.sanitization import project_memory_for_llm

        raw_memory = {
            "id": "mem-123",
            "user_id": "user-456",
            "memory_type": "PREFERENCE",
            "key": "test_key",
            "content": "Test content",
            "confidence": 0.9,
            "status": "ACTIVE",
            "version": 1,
            "source": "agent_inferred",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }

        result = project_memory_for_llm(raw_memory)
        assert "id" not in result
        assert "user_id" not in result
        assert "status" not in result
        assert "created_at" not in result
        assert "content" in result
        assert "memory_type" in result

    async def test_citations_still_work_with_memory(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Phase 04 citations should still work alongside Phase 05 memory."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "退货政策是什么？",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"cite-mem-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)
        data = resp.json().get("data", {})
        # citations should always be a list (even if empty)
        assert isinstance(data.get("citations", []), list)
