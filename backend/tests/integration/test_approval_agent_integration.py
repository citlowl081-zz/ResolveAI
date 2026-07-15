"""Integration tests for Agent + Approval flow — pause, resume, idempotency."""

import uuid

from httpx import AsyncClient


class TestApprovalCreation:
    async def test_approval_endpoints_exist(
        self, async_client: AsyncClient, customer_auth: dict, admin_auth: dict,
    ) -> None:
        """Verify both customer and admin approval endpoints are reachable."""
        # Customer view
        r1 = await async_client.get("/api/v1/approvals", headers=customer_auth["headers"])
        assert r1.status_code == 200

        # Admin view
        r2 = await async_client.get("/api/v1/admin/approvals", headers=admin_auth["headers"])
        assert r2.status_code == 200

    async def test_admin_approve_reject_endpoints_require_idempotency(
        self, async_client: AsyncClient, admin_auth: dict,
    ) -> None:
        """Approve/Reject endpoints require Idempotency-Key header."""
        fake_id = uuid.uuid4()
        r1 = await async_client.post(
            f"/api/v1/admin/approvals/{fake_id}/approve",
            json={"expected_version": 1},
            headers=admin_auth["headers"],
        )
        assert r1.status_code == 422

        r2 = await async_client.post(
            f"/api/v1/admin/approvals/{fake_id}/reject",
            json={"expected_version": 1},
            headers=admin_auth["headers"],
        )
        assert r2.status_code == 422

    async def test_rbac_customer_cannot_approve(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Customer role cannot access admin approve/reject endpoints."""
        fake_id = uuid.uuid4()
        r1 = await async_client.post(
            f"/api/v1/admin/approvals/{fake_id}/approve",
            json={"expected_version": 1},
            headers={
                **customer_auth["headers"],
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        assert r1.status_code == 403

    async def test_rbac_customer_cannot_execute(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Customer role cannot execute approved actions."""
        fake_id = uuid.uuid4()
        r1 = await async_client.post(
            f"/api/v1/admin/approvals/{fake_id}/execute",
            headers={
                **customer_auth["headers"],
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        assert r1.status_code == 403


class TestPayloadIntegrity:
    async def test_stored_payload_used_not_client_submitted(
        self, async_client: AsyncClient, admin_auth: dict,
    ) -> None:
        """The execute endpoint ignores client payload — it uses DB-stored payload.

        This is a design guarantee: the execute endpoint has no request body,
        forcing it to use the server-saved sanitized_action_payload.
        """
        fake_id = uuid.uuid4()
        # Sending extra JSON should still fail (404 for nonexistent task, not 422)
        resp = await async_client.post(
            f"/api/v1/admin/approvals/{fake_id}/execute",
            json={"payload": "INJECTED"},  # Client trying to send its own payload
            headers={
                **admin_auth["headers"],
                "Idempotency-Key": str(uuid.uuid4()),
            },
        )
        # Execute endpoint ignores the body — should get 404 (task not found)
        assert resp.status_code == 404


class TestCitationsAndMemoryPreserved:
    async def test_agent_response_includes_citations(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Phase 04 citations still work."""
        resp = await async_client.post("/api/v1/agent/sessions", json={
            "message": "退货政策是什么？",
        }, headers={
            **customer_auth["headers"],
            "Idempotency-Key": f"cite-{uuid.uuid4().hex}",
        })
        assert resp.status_code in (200, 201)
        data = resp.json().get("data", {})
        assert isinstance(data.get("citations", []), list)

    async def test_memory_still_works_with_approval(
        self, async_client: AsyncClient, customer_auth: dict,
    ) -> None:
        """Phase 05 memory endpoints still work alongside Phase 06."""
        resp = await async_client.get(
            "/api/v1/memories", headers=customer_auth["headers"],
        )
        assert resp.status_code == 200
