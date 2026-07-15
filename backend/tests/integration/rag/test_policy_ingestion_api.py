"""Integration tests for Admin Policy API — CRUD, ingestion, status transitions."""

import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings

_ENGINE = create_async_engine(
    settings.resolved_database_url, pool_size=2, max_overflow=2, pool_pre_ping=True,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(_ENGINE, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _cleanup(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    yield
    try:
        await db_session.execute(text("DELETE FROM policy_chunks"))
        await db_session.execute(text("DELETE FROM policy_documents"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


async def _register_admin(client: AsyncClient) -> dict:
    email = f"adm-{uuid.uuid4().hex[:6]}@test.com"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "admin123", "full_name": "Admin",
    })
    # Upgrade to ADMIN via DB
    engine2 = create_async_engine(settings.resolved_database_url, pool_size=1, max_overflow=1, pool_pre_ping=True)
    async with engine2.connect() as conn:
        await conn.execute(text("UPDATE users SET role='ADMIN' WHERE email=:e"), {"e": email})
        await conn.commit()
    await engine2.dispose()

    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "admin123"})
    data = resp.json()["data"]
    return {"headers": {"Authorization": f"Bearer {data['access_token']}"}, "user": data["user"]}


async def _create_product(client: AsyncClient, admin: dict) -> dict:
    r = await client.post("/api/v1/products", json={
        "name": f"P-{uuid.uuid4().hex[:4]}", "category": "ELECTRONICS",
        "price": "199.99", "stock": 50,
    }, headers=admin["headers"])
    return r.json()["data"]  # type: ignore[no-any-return]


class TestAdminPolicyCRUD:
    async def test_create_and_get_active(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        key = f"POL-REF-{f"{uuid.uuid4().int % 1000:03d}"}"
        r = await async_client.post("/api/v1/admin/policies", json={
            "policy_key": key, "title": "测试退款规则", "category": "REFUND",
            "content": "测试退款政策正文内容。", "effective_date": "2025-01-01",
            "status": "ACTIVE",
        }, headers=admin["headers"])
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["policy_key"] == key
        assert data["status"] == "ACTIVE"

        # GET by-key
        r2 = await async_client.get(
            f"/api/v1/admin/policies/by-key/{key}", headers=admin["headers"],
        )
        assert r2.status_code == 200
        assert r2.json()["data"]["status"] == "ACTIVE"

    async def test_get_active_returns_404_when_none(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        r = await async_client.get(
            "/api/v1/admin/policies/by-key/POL-REF-999", headers=admin["headers"],
        )
        assert r.status_code == 404
        assert r.json()["code"] == "POLICY_ACTIVE_NOT_FOUND"

    async def test_list_policies(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        for i in range(3):
            await async_client.post("/api/v1/admin/policies", json={
                "policy_key": f"POL-REF-{i:03d}", "title": f"规则{i}",
                "category": "REFUND", "content": f"内容{i}",
                "effective_date": "2025-01-01", "status": "ACTIVE",
            }, headers=admin["headers"])

        r = await async_client.get(
            "/api/v1/admin/policies", headers=admin["headers"],
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] >= 3

    async def test_update_creates_new_draft(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        key = f"POL-REF-{f"{uuid.uuid4().int % 1000:03d}"}"
        await async_client.post("/api/v1/admin/policies", json={
            "policy_key": key, "title": "原版", "category": "REFUND",
            "content": "原内容。", "effective_date": "2025-01-01", "status": "ACTIVE",
        }, headers=admin["headers"])

        # Update
        r = await async_client.put(f"/api/v1/admin/policies/by-key/{key}", json={
            "title": "新版", "category": "REFUND", "content": "新内容。",
            "effective_date": "2025-01-01",
        }, headers=admin["headers"])
        assert r.status_code == 200
        assert r.json()["data"]["version"] == 2
        assert r.json()["data"]["status"] == "DRAFT"

    async def test_activate_draft_supersedes_active(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        key = f"POL-REF-{f"{uuid.uuid4().int % 1000:03d}"}"
        await async_client.post("/api/v1/admin/policies", json={
            "policy_key": key, "title": "V1", "category": "REFUND",
            "content": "V1内容。", "effective_date": "2025-01-01", "status": "ACTIVE",
        }, headers=admin["headers"])

        # Create a DRAFT v2
        r2 = await async_client.put(f"/api/v1/admin/policies/by-key/{key}", json={
            "title": "V2", "category": "REFUND", "content": "V2内容。",
            "effective_date": "2025-01-01",
        }, headers=admin["headers"])
        v2 = r2.json()["data"]

        # Activate v2
        r3 = await async_client.patch(
            f"/api/v1/admin/policies/by-key/{key}/versions/{v2['version']}/status",
            json={"status": "ACTIVE"}, headers=admin["headers"],
        )
        assert r3.status_code == 200

        # GET active should return v2
        r4 = await async_client.get(
            f"/api/v1/admin/policies/by-key/{key}", headers=admin["headers"],
        )
        assert r4.json()["data"]["version"] == v2["version"]

    async def test_version_history(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        key = f"POL-REF-{f"{uuid.uuid4().int % 1000:03d}"}"
        for _ in range(2):
            await async_client.put(f"/api/v1/admin/policies/by-key/{key}", json={
                "title": f"V{key}", "category": "REFUND",
                "content": f"内容{uuid.uuid4().hex[:4]}。", "effective_date": "2025-01-01",
            }, headers=admin["headers"])

        r = await async_client.get(
            f"/api/v1/admin/policies/by-key/{key}/versions", headers=admin["headers"],
        )
        assert r.status_code == 200
        items = r.json()["data"]["items"]
        assert len(items) >= 2

    async def test_non_admin_rejected(
        self, async_client: AsyncClient,
    ) -> None:
        r = await async_client.post("/api/v1/admin/policies", json={
            "policy_key": "POL-REF-001", "title": "X", "category": "REFUND",
            "content": "X。", "effective_date": "2025-01-01",
        })
        assert r.status_code in (401, 403)


class TestIngestion:
    async def test_ingest_all_policies(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        r = await async_client.post(
            "/api/v1/admin/policies/ingest",
            json={"activate": True}, headers=admin["headers"],
        )
        assert r.status_code == 200
        report = r.json()["data"]["report"]
        assert len(report) >= 14

    async def test_ingest_then_search(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        # Ingest
        await async_client.post(
            "/api/v1/admin/policies/ingest",
            json={"activate": True}, headers=admin["headers"],
        )
        # Search from the service layer — best effort check that data exists
        from app.rag.embeddings import build_embedding_provider
        from app.services.policy_service import PolicyService
        factory = async_sessionmaker(_ENGINE, class_=AsyncSession, expire_on_commit=False)
        provider = build_embedding_provider()
        svc = PolicyService(session_factory=factory, embedding_provider=provider)
        results = await svc.search("退款", top_k=3)
        assert len(results) >= 1


class TestStatusTransitions:
    async def test_archive_active(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        key = f"POL-REF-{f"{uuid.uuid4().int % 1000:03d}"}"
        r = await async_client.post("/api/v1/admin/policies", json={
            "policy_key": key, "title": "T", "category": "REFUND",
            "content": "C。", "effective_date": "2025-01-01", "status": "ACTIVE",
        }, headers=admin["headers"])
        v = r.json()["data"]["version"]

        r2 = await async_client.patch(
            f"/api/v1/admin/policies/by-key/{key}/versions/{v}/status",
            json={"status": "ARCHIVED"}, headers=admin["headers"],
        )
        assert r2.status_code == 200
        assert r2.json()["data"]["status"] == "ARCHIVED"

    async def test_cannot_transition_from_superseded(
        self, async_client: AsyncClient,
    ) -> None:
        admin = await _register_admin(async_client)
        key = f"POL-REF-{f"{uuid.uuid4().int % 1000:03d}"}"
        r = await async_client.post("/api/v1/admin/policies", json={
            "policy_key": key, "title": "V1", "category": "REFUND",
            "content": "C1。", "effective_date": "2025-01-01", "status": "ACTIVE",
        }, headers=admin["headers"])

        r2 = await async_client.put(f"/api/v1/admin/policies/by-key/{key}", json={
            "title": "V2", "category": "REFUND", "content": "C2。",
            "effective_date": "2025-01-01",
        }, headers=admin["headers"])
        v2 = r2.json()["data"]["version"]

        # Activate v2 (makes v1 SUPERSEDED)
        await async_client.patch(
            f"/api/v1/admin/policies/by-key/{key}/versions/{v2}/status",
            json={"status": "ACTIVE"}, headers=admin["headers"],
        )

        # Try to archive v1 (SUPERSEDED → ARCHIVED is invalid)
        r3 = await async_client.patch(
            f"/api/v1/admin/policies/by-key/{key}/versions/{r.json()['data']['version']}/status",
            json={"status": "ARCHIVED"}, headers=admin["headers"],
        )
        assert r3.status_code == 409
