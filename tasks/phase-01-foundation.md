# Phase 01 — Project Foundation

## Phase Goals

Set up the complete backend project skeleton with FastAPI application, SQLAlchemy models, Alembic migrations, and initial seed data. Establish the development workflow with linting, type checking, and testing infrastructure.

## Preconditions

- Phase 00 completed.
- Python 3.12 installed.
- PostgreSQL 16 running (via Docker or local).
- LLM API key available (for future phases, not required for this phase).

## Task Checklist

### 1.1 Backend Project Setup
- [ ] Create `backend/pyproject.toml` with dependencies.
- [ ] Create `backend/Dockerfile`.
- [ ] Install dependencies: FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, asyncpg, pgvector, LangGraph, pytest, Ruff, mypy.
- [ ] Configure Ruff (pyproject.toml [tool.ruff]).
- [ ] Configure mypy (pyproject.toml [tool.mypy]).
- [ ] Configure pytest (pyproject.toml [tool.pytest.ini_options]).

### 1.2 Configuration
- [ ] Implement `app/config/settings.py` — load from environment with Pydantic Settings.
- [ ] Configure database URL, JWT settings, LLM settings, CORS origins.
- [ ] Implement `app/main.py` — FastAPI app factory with CORS, routers, lifespan.

### 1.3 Database
- [ ] Implement `app/database/engine.py` — async SQLAlchemy engine.
- [ ] Implement `app/database/session.py` — async session factory with dependency injection.
- [ ] Implement `app/database/base.py` — declarative base with common columns (UUID PK, created_at, updated_at).

### 1.4 SQLAlchemy Models (All 17 Tables)
- [ ] `User` model with role enum.
- [ ] `Product` model with category enum.
- [ ] `Order` model with status enum, version for optimistic locking.
- [ ] `OrderItem` model.
- [ ] `LogisticsRecord` model with JSONB events.
- [ ] `AfterSalesTicket` model with idempotency_key, version.
- [ ] `RefundRecord` model with idempotency_key, version.
- [ ] `ReshipmentOrder` model with idempotency_key, version.
- [ ] `ApprovalTask` model.
- [ ] `AgentSession` model with JSONB graph_state.
- [ ] `AgentMessage` model.
- [ ] `AgentToolLog` model.
- [ ] `AgentTrace` model.
- [ ] `CustomerMemory` model.
- [ ] `PolicyDocument` model with pgvector embedding column.
- [ ] `AuditLog` model.
- [ ] `SystemConfig` model.

### 1.5 Alembic Migrations
- [ ] Initialize Alembic: `alembic init`.
- [ ] Configure Alembic for async SQLAlchemy.
- [ ] Generate initial migration with all tables.
- [ ] Create all PostgreSQL enums in migration.
- [ ] Set up pgvector extension in migration.
- [ ] Test: `alembic upgrade head` + `alembic downgrade -1`.

### 1.6 Seed Data
- [ ] Implement `app/database/seed.py` — seed script.
- [ ] Create 3 test users (customer, operator, admin).
- [ ] Create 10 sample products across categories.
- [ ] Create 3 sample orders with various statuses.
- [ ] Seed data runs on first startup (idempotent).

### 1.7 API Skeleton
- [ ] Implement `app/api/__init__.py` — router aggregation.
- [ ] Implement `app/api/auth.py` — register, login, refresh, me.
- [ ] Implement `app/api/products.py` — list, detail.
- [ ] Implement health check endpoint.

### 1.8 Security Foundation
- [ ] Implement JWT token generation and validation.
- [ ] Implement password hashing with bcrypt.
- [ ] Implement role-based dependency injection.
- [ ] Implement PII masking utilities.

### 1.9 Testing Infrastructure
- [ ] Create test fixtures (DB session, test client, test data).
- [ ] Write unit tests for config loading.
- [ ] Write integration tests for database connection and migrations.
- [ ] Write integration tests for auth endpoints.
- [ ] Write integration tests for product endpoints.
- [ ] Write model validation tests (enum constraints, unique constraints).

### 1.10 Observability Foundation
- [ ] Implement structured logging with structlog or loguru.
- [ ] Implement request ID middleware.
- [ ] Implement PII mask filter for logs.

## Expected Directory Changes

```
backend/
├── pyproject.toml          [NEW]
├── Dockerfile              [NEW]
├── alembic.ini             [NEW]
├── alembic/
│   ├── env.py              [NEW]
│   └── versions/
│       └── 001_initial.py  [NEW]
└── app/
    ├── __init__.py         [NEW]
    ├── main.py             [NEW]
    ├── config/
    │   ├── __init__.py     [NEW]
    │   └── settings.py     [NEW]
    ├── database/
    │   ├── __init__.py     [NEW]
    │   ├── engine.py       [NEW]
    │   ├── session.py      [NEW]
    │   ├── base.py         [NEW]
    │   └── seed.py         [NEW]
    ├── models/
    │   ├── __init__.py     [NEW]
    │   ├── user.py         [NEW]
    │   ├── product.py      [NEW]
    │   ├── order.py        [NEW]
    │   ├── ticket.py       [NEW]
    │   ├── refund.py       [NEW]
    │   ├── ... (all models) [NEW]
    ├── api/
    │   ├── __init__.py     [NEW]
    │   ├── auth.py         [NEW]
    │   └── products.py     [NEW]
    ├── security/
    │   ├── __init__.py     [NEW]
    │   ├── jwt.py          [NEW]
    │   ├── password.py     [NEW]
    │   └── pii.py          [NEW]
    └── observability/
        ├── __init__.py     [NEW]
        └── logging.py      [NEW]
```

## Database Changes

- All 17 tables created.
- 18 PostgreSQL enums created.
- pgvector extension enabled.
- All indexes and constraints.

## Testing Requirements

- [ ] All model definitions load without error.
- [ ] Migration runs up and down cleanly.
- [ ] Seed data is idempotent.
- [ ] Auth: register → login → access protected endpoint.
- [ ] Products: list returns paginated results.
- [ ] Ruff passes.
- [ ] mypy passes.
- [ ] pytest passes (all tests).

## Acceptance Criteria

- [ ] `alembic upgrade head` creates all tables in PostgreSQL.
- [ ] `alembic downgrade -1` drops all tables cleanly.
- [ ] Seeded users can log in.
- [ ] Seeded products are queryable via API.
- [ ] JWT tokens work for authentication.
- [ ] All tests pass.
- [ ] Ruff and mypy pass with no errors.

## Risks

- Alembic async configuration can be tricky with pgvector.
- Enum synchronization between Python and PostgreSQL requires care.
- Seed data must handle idempotent re-runs.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
- **Reviewer:** Self
