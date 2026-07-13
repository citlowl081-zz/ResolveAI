# Phase 01 — Project Foundation

## Phase Goals

Set up the backend project skeleton (FastAPI app factory, configuration, health check, database infrastructure), PostgreSQL + pgvector via Docker Compose, Alembic initialization (pgvector extension only, no business tables), two Next.js frontend scaffolds, testing infrastructure, and CI pipeline. Establish the development workflow with linting, type checking, and testing.

## Revision History

- **2026-07-13 (original):** Initial plan from Phase 00 — scope was too broad, included all 17 business models, 18 enums, JWT auth, product API, seed data.
- **2026-07-13 (revision):** Scoped down per user direction. Business models, enums, auth, product API, order API, Service layer, Repository layer, seed data moved to Phase 02.

## Preconditions

- Phase 00 completed.
- Python 3.12 installed (`/opt/homebrew/bin/python3.12` or in PATH as `python3.12`).
- Node.js 20+ installed.
- Docker + Docker Compose installed.

## Task Checklist

### 1.1 Backend Project Setup
- [ ] Create `backend/pyproject.toml` with dependencies (FastAPI, uvicorn, SQLAlchemy 2, asyncpg, Pydantic 2, Pydantic-Settings, structlog, Alembic, pgvector) and dev dependencies (pytest, pytest-asyncio, httpx, Ruff, mypy).
- [ ] Create `backend/Dockerfile` (multi-stage: builder + runtime).
- [ ] Create `backend/.venv` via `/opt/homebrew/bin/python3.12 -m venv backend/.venv`.
- [ ] Install dependencies: `pip install -e ".[dev]"`.
- [ ] Configure Ruff (`[tool.ruff]` in pyproject.toml).
- [ ] Configure mypy (`[tool.mypy]` in pyproject.toml).
- [ ] Configure pytest (`[tool.pytest.ini_options]` in pyproject.toml).

### 1.2 Configuration
- [ ] Implement `app/config/settings.py` — Pydantic Settings from environment; fields: DATABASE_URL, APP_ENV, DEBUG, LOG_LEVEL, CORS_ORIGINS, POSTGRES_*.
- [ ] Implement `app/main.py` — FastAPI app factory with CORS, router registration, lifespan (DB engine connect/disconnect), exception handler registration.

### 1.3 Common Infrastructure
- [ ] Implement `app/schemas/common.py` — `APIResponse[T]` generic envelope, `Pagination` model.
- [ ] Implement `app/exceptions.py` — unified exception hierarchy: `AppError` base → `NotFoundError`, `ValidationError`, `ConflictError`, `InternalError`.
- [ ] Implement `app/observability/logging.py` — structlog configuration, request ID middleware, basic PII mask filter.

### 1.4 Database Infrastructure (No Business Tables)
- [ ] Implement `app/database/engine.py` — `create_async_engine` with asyncpg driver.
- [ ] Implement `app/database/session.py` — `async_sessionmaker` + FastAPI dependency `get_db`.
- [ ] Implement `app/database/base.py` — SQLAlchemy `DeclarativeBase`, `TimestampMixin` (UUID PK, created_at, updated_at).

### 1.5 Health Check
- [ ] Implement `app/api/health.py` — `GET /api/v1/health` returns DB connection status.
- [ ] Register health router in `app/api/__init__.py`.

### 1.6 Docker Compose
- [ ] Verify `docker-compose.yml`: pgvector/pgvector:pg16 image, healthcheck, port 5432, volume, environment.
- [ ] `docker compose up -d db` — PostgreSQL starts and passes healthcheck.

### 1.7 Alembic Initialization
- [ ] Initialize Alembic: `alembic init`.
- [ ] Configure `alembic/env.py` for async SQLAlchemy (use `DATABASE_URL` from settings, async engine).
- [ ] Create migration `001_enable_pgvector.py` — `CREATE EXTENSION IF NOT EXISTS vector` (upgrade) + `DROP EXTENSION IF EXISTS vector` (downgrade).
- [ ] Test: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`.

### 1.8 Frontend Scaffolding
- [ ] Initialize `frontend/customer-web` via `npx create-next-app@latest`.
- [ ] Initialize `frontend/admin-web` via `npx create-next-app@latest`.
- [ ] Both projects: TypeScript, Tailwind CSS, ESLint, `tsconfig.json` strict mode.
- [ ] Both projects: minimal `page.tsx` with "ResolveAI" placeholder.
- [ ] Record actual installed versions (Next.js, React, TypeScript, Node minimum).
- [ ] Commit `package.json` and `package-lock.json`.

### 1.9 Testing Infrastructure
- [ ] Create `backend/tests/conftest.py` — async test client fixture (`httpx.AsyncClient`), test DB session fixture.
- [ ] Write `tests/unit/test_config.py` — settings load from env, defaults, validation.
- [ ] Write `tests/unit/test_schemas.py` — APIResponse success/error serialization, Pagination.
- [ ] Write `tests/integration/test_health.py` — `GET /api/v1/health` returns 200, DB connected.
- [ ] Write `tests/integration/test_db.py` — engine connects, session executes query.

### 1.10 CI Pipeline
- [ ] Create `.github/workflows/ci.yml` — jobs: lint (Ruff), typecheck (mypy), test (pytest), frontend-customer (lint+typecheck+build), frontend-admin (lint+typecheck+build).
- [ ] Python 3.12 via `actions/setup-python@v5`.
- [ ] Node.js via `actions/setup-node@v4`.
- [ ] PostgreSQL service container for tests.

### 1.11 Makefile & Environment
- [ ] Update `Makefile` — `PYTHON ?= python3.12`, `VENV := backend/.venv`, venv target, install, test, lint, typecheck, dev-backend, docker-* commands.
- [ ] Update `.env.example` — align all variable names with `settings.py`.

## Moved to Phase 02

The following were originally planned for Phase 01 but have been deferred:
- All 17 SQLAlchemy business models (User, Product, Order, OrderItem, LogisticsRecord, AfterSalesTicket, RefundRecord, ReshipmentOrder, ApprovalTask, AgentSession, AgentMessage, AgentToolLog, AgentTrace, CustomerMemory, PolicyDocument, AuditLog, SystemConfig)
- All 18 PostgreSQL business enums
- User registration and login (JWT auth)
- Password hashing (bcrypt)
- Role-based access control dependencies
- Product API (list/detail)
- Order API
- Business Service layer
- Business Repository layer
- Business rule engine
- Seed data
- Complete business migration

## Database Changes (This Phase)

- **pgvector extension enabled only.**
- No tables, no enums, no seed data.

## API Changes (This Phase)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | No | Health check with DB status |

## Testing Requirements

- [ ] `ruff check` passes (zero errors).
- [ ] `mypy` passes (zero errors).
- [ ] `pytest tests/unit/` passes.
- [ ] `pytest tests/integration/` passes (requires PostgreSQL).
- [ ] Health endpoint returns 200 with DB connected.
- [ ] Alembic upgrade/downgrade works cleanly.

## Acceptance Criteria

- [ ] `ruff check app/ tests/` — zero errors.
- [ ] `mypy app/ tests/` — zero errors.
- [ ] `pytest -v` — all tests pass.
- [ ] `GET /api/v1/health` responds with `{"success": true, "data": {"status": "healthy", "database": "connected"}}`.
- [ ] `docker compose up -d db` — PostgreSQL healthy within 30s.
- [ ] `alembic upgrade head` — pgvector extension created.
- [ ] `alembic downgrade -1` — pgvector extension dropped, clean state.
- [ ] `customer-web`: `npm run lint` + `npm run typecheck` + `npm run build` all pass.
- [ ] `admin-web`: `npm run lint` + `npm run typecheck` + `npm run build` all pass.
- [ ] `.github/workflows/ci.yml` passes syntax validation.
- [ ] `Makefile` targets work: `make venv`, `make install`, `make test`, `make lint`, `make typecheck`.

## Risks

- Alembic async configuration requires careful setup of `env.py`.
- Next.js `create-next-app@latest` version is non-deterministic; versions recorded at creation time.
- pgvector extension requires superuser or specific privileges on the PostgreSQL instance.
- Docker daemon must be running for DB steps and integration tests.

## Completion Record

- **Started:** 2026-07-13
- **Completed:** TBD
- **Actual Effort:** TBD
- **Reviewer:** Self
