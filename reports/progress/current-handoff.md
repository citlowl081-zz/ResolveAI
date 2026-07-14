# ResolveAI — Current Handoff

**Date:** 2026-07-14  
**Generated:** Before context compression

---

## Current Phase

**Phase 02B — After-sales Business Backend** (PLANNING, awaiting approval)

Phase 02A is complete. Phase 02B plan has been designed and is awaiting user review. No Phase 02B code has been written.

---

## Completed Content

### Phase 00 — Planning
- Complete project documentation (12 design docs + 4 ADRs)
- Task tracking for all 10 phases
- Directory structure

### Phase 01 — Project Foundation
- FastAPI app factory with CORS, lifespan, exception handlers
- Pydantic Settings configuration
- Async SQLAlchemy engine, session, Base + TimestampMixin
- `GET /health` endpoint
- PostgreSQL 16 + pgvector 0.8.5 via Docker Compose
- Alembic with pgvector extension migration (001)
- Next.js 14 customer-web + admin-web scaffolds
- Ruff, mypy, pytest infrastructure
- GitHub Actions CI pipeline

### Phase 02A — Core Commerce Backend
- 8 tables: users, products, orders, order_items, logistics_records, audit_logs, system_configs, idempotency_records
- 5 PostgreSQL enums: user_role, risk_level, product_category, order_status (PENDING_PAYMENT/PAID/SHIPPED/DELIVERED/CANCELLED), logistics_status
- 18 API endpoints across 5 routers
- JWT auth (access + refresh tokens with type enforcement)
- RBAC: CUSTOMER/OPERATOR/ADMIN with server-side enforcement
- Order lifecycle: create → pay → ship → deliver → cancel (PENDING_PAYMENT only)
- Duplicate product aggregation + UNIQUE(order_id, product_id)
- In-transaction idempotency: INSERT ON CONFLICT DO NOTHING RETURNING
- Optimistic locking via version column on all mutating operations
- SELECT FOR UPDATE with sorted product IDs for deadlock prevention
- All monetary types: NUMERIC(12,2) → Python Decimal
- Audit logging with field-level PII sanitization
- Idempotent seed script (5 users, 10 products, 4 orders)
- 33 self-contained integration tests (no seed dependency)
- CI green on GitHub Actions (after 4 fix rounds)

---

## Latest Commit

```
5bbdf6b [Phase 02A] Fix request transaction persistence and test isolation
```

Full commit chain (most recent first):
```
5bbdf6b Fix request transaction persistence and test isolation
e5614b1 Fix CI runtime dependencies and clean-room validation
598e155 Fix redundant casts in security type boundaries
4e3fe52 Fix CI mypy errors in security boundaries
ebabc63 Complete: 32 tests pass, Ruff 0, Mypy 0
```

---

## Latest Remote CI Status

**ALL GREEN** (last run on commit `5bbdf6b` after 4 CI fix rounds):
- Backend — Lint & Typecheck: PASS
- Backend — Tests: PASS (33/33)
- Frontend — Customer Web: PASS
- Frontend — Admin Web: PASS

---

## Current Database Migrations

```
bc03591cd96c (head) — create_core_commerce_tables
a33b3199a4a2        — enable_pgvector_extension
```

8 tables: users, products, orders, order_items, logistics_records, audit_logs, system_configs, idempotency_records

5 enums: user_role, risk_level, product_category, order_status, logistics_status

---

## Implemented API Endpoints (18)

### Auth (4)
- `POST /api/v1/auth/register` — public
- `POST /api/v1/auth/login` — public
- `POST /api/v1/auth/refresh` — refresh token
- `GET /api/v1/auth/me` — access token

### Products (4)
- `GET /api/v1/products` — public, paginated, filterable
- `GET /api/v1/products/{id}` — public
- `POST /api/v1/products` — ADMIN
- `PATCH /api/v1/products/{id}` — ADMIN, version check

### Orders (7)
- `POST /api/v1/orders` — CUSTOMER, Idempotency-Key
- `GET /api/v1/orders` — CUSTOMER, own orders
- `GET /api/v1/orders/{id}` — owner/ADMIN/OPERATOR
- `POST /api/v1/orders/{id}/pay` — owner, Idempotency-Key, version check
- `POST /api/v1/orders/{id}/cancel` — owner/ADMIN, Idempotency-Key (PENDING_PAYMENT only)
- `POST /api/v1/orders/{id}/ship` — ADMIN/OPERATOR, Idempotency-Key
- `POST /api/v1/orders/{id}/deliver` — ADMIN/OPERATOR, Idempotency-Key

### Logistics (2)
- `GET /api/v1/orders/{id}/logistics` — owner/ADMIN/OPERATOR
- `POST /api/v1/orders/{id}/logistics/events` — ADMIN/OPERATOR, Idempotency-Key

### Admin (1)
- `GET /api/v1/admin/config` — ADMIN

### Health (1)
- `GET /health` — public

---

## Key Architecture Decisions

1. **Transaction ownership:** `get_db` commits on success, rolls back on exception. Services call `session.flush()` internally. No commit in Repository or Service.
2. **Idempotency:** Single `idempotency_records` table with INSERT ON CONFLICT DO NOTHING RETURNING pattern. `UNIQUE(user_id, operation, idempotency_key)`. No FAILED status — business failure rolls back entire tx.
3. **Optimistic locking:** `version` column on users, products, orders. All mutating endpoints require `expected_version` in request body. `WHERE version = :expected RETURNING version` → 0 rows = 409.
4. **Monetary precision:** PostgreSQL `NUMERIC(12,2)` → Python `Decimal`. No `float`. Client cannot submit prices/amounts.
5. **Stock management:** Pre-check at order create (non-locking). Deduction at pay (SELECT FOR UPDATE, sorted ascending by product_id). No reservation.
6. **PAID cancel deferred:** PAID/SHIPPED/DELIVERED orders cannot be cancelled via Phase 02A cancel endpoint → returns 409, directs to after-sales flow (Phase 02B).
7. **Test isolation:** All tests self-contained (create own data via API). No dependency on seed data. Fresh database per test suite. Unique emails per test.
8. **CI deps:** `email-validator`, `types-passlib`, `types-python-jose` declared in pyproject.toml dev deps. `bcrypt<5` pinned for passlib compatibility.

---

## Known Limitations

1. **No PAID order cancellation** — returns 409 "use after-sales process" → Phase 02B
2. **No server-side Refresh Token revocation** — short TTL (30 min) partially mitigates
3. **No payment gateway** — payment is simulated status transition
4. **No shopping cart** — direct order creation
5. **No inventory reservation** — stock checked at create, deducted at pay
6. **bcrypt 5.x incompatible with passlib** — pinned `bcrypt<5`
7. **npm cache has root-owned files** — workaround with `/tmp/npm-cache-fresh`
8. **order_items has no refund tracking fields** — Phase 02B adds `refunded_quantity`/`reshipped_quantity`

---

## Uncommitted Changes

Three task files modified (PLANNING ONLY, no code changes):

```
tasks/active-phase.md              — Updated to Phase 02B
tasks/phase-02-business-backend.md — Updated index with Phase 02A summary
tasks/phase-02B-after-sales.md     — Full Phase 02B design document
```

**No code, migration, or test files were modified.**

---

## Next Task

**Phase 02B — After-sales Business Backend** implementation (pending user approval of plan):

1. Create migration 003 (3 tables + 6 enums + order_status extension + order_items ALTER)
2. Implement 3 SQLAlchemy models + 6 Python enums
3. Implement eligibility rules (7 reject codes, NEEDS_REVIEW triggers)
4. Implement refund calculator (Decimal, cap enforcement)
5. Implement Ticket/Refund/Reshipment services (transactional)
6. Extend order state transitions (REFUNDING/REFUNDED)
7. Extend cancel endpoint (PAID → auto-refund + stock restore)
8. Implement after-sales API endpoints (customer + admin)
9. Write self-contained integration tests
10. Ruff, mypy, pytest, CI verification

---

## Start & Test Commands

```bash
# PostgreSQL
docker compose up -d db

# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Seed data
python -m app.database.seed

# Full check
ruff check app/ tests/
mypy --no-incremental app/ tests/
pytest -v

# Fresh test database (recreate + run)
docker exec resolveai-db psql -U resolveai -d resolveai -c "DROP DATABASE IF EXISTS resolveai_test_ci;"
docker exec resolveai-db psql -U resolveai -d resolveai -c "CREATE DATABASE resolveai_test_ci;"
DATABASE_URL="postgresql+asyncpg://resolveai:resolveai-dev@localhost:5432/resolveai_test_ci" alembic upgrade head
DATABASE_URL="postgresql+asyncpg://resolveai:resolveai-dev@localhost:5432/resolveai_test_ci" pytest -v

# Frontend
cd frontend/customer-web && npm run dev   # :3000
cd frontend/admin-web && npm run dev      # :3001

# Docker full stack
docker compose up -d
```

### Test Accounts (from seed)

| Email | Password | Role |
|-------|----------|------|
| admin@test.com | password123 | ADMIN |
| operator@test.com | password123 | OPERATOR |
| customer@test.com | password123 | CUSTOMER |
