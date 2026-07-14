# ResolveAI — Current Handoff

**Date:** 2026-07-14
**Generated:** After Phase 02B completion and remote CI verification

---

## Current Phase

**Phase 02 — Business Backend: COMPLETE**

Both sub-phases (02A Core Commerce + 02B After-sales) are complete, tested, and CI-verified. Next phase is Phase 03 — Agent Tools (planning not yet started).

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
- 5 PostgreSQL enums: user_role, risk_level, product_category, order_status, logistics_status
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
- 33 self-contained integration tests (no seed dependency)

### Phase 02B — After-sales Business Backend
- 3 new tables: after_sales_tickets, refund_records, reshipment_orders
- 5 new enums: intent_type, ticket_status, resolution_type, refund_type, reshipment_status
- order_status extended: +REFUNDED
- order_items extended: +refunded_quantity, +reshipped_quantity
- 2 PostgreSQL sequences: ticket_number_seq, reshipment_number_seq
- 13 API endpoints (4 customer + 9 operator/admin)
- Ticket lifecycle: create → auto-validate (APPROVED/REJECTED/NEEDS_REVIEW) → execute (COMPLETED/NEEDS_REVIEW)
- 7 reject codes: NOT_OWNER, INVALID_STATUS, DUPLICATE_TICKET, NOT_RETURNABLE, OVER_TIME_LIMIT, QUANTITY_EXCEEDED, ALREADY_REFUNDED
- Refund calculator: deterministic Decimal, cumulative cap, shipping fee cap
- Lock ordering: ticket → order → order_items → products with post-lock re-validation
- Cross-key duplicate guard: UNIQUE(ticket_id) on refund_records + reshipment_orders
- Active ticket dedup: partial unique index (order_id, intent, request_fingerprint)
- 6-assertion downgrade protection
- No PROCESSING transient states, no refund_status enum
- 16 new integration tests (49 total), CI green

---

## Latest Remote CI Status

**ALL GREEN** — GitHub Actions remote CI verified:

- Backend — Lint & Typecheck: PASS
- Backend — Tests: PASS (49/49)
- Frontend — Customer Web: PASS
- Frontend — Admin Web: PASS

---

## Current Database Migrations

```
003 (head) — create_after_sales_tables
bc03591cd96c — create_core_commerce_tables
a33b3199a4a2 — enable_pgvector_extension
```

12 tables: users, products, orders, order_items, logistics_records, audit_logs, system_configs, idempotency_records, after_sales_tickets, refund_records, reshipment_orders, alembic_version

10 enums: user_role, risk_level, product_category, order_status (+REFUNDED), logistics_status, intent_type, ticket_status, resolution_type, refund_type, reshipment_status

---

## Implemented API Endpoints (31)

### Phase 02A (18)
- 4 Auth: register, login, refresh, me
- 4 Products: list, detail, create (ADMIN), update (ADMIN)
- 7 Orders: create, list, detail, pay, cancel, ship, deliver
- 2 Logistics: list, add event
- 1 Admin: config read

### Phase 02B (13)
- 4 Customer after-sales: create ticket, list tickets, ticket detail, cancel ticket
- 6 Admin after-sales: list all, ticket detail, approve, reject, refund, reship
- 3 Admin reshipments: ship, deliver, cancel

---

## Key Architecture Decisions

1. **Transaction ownership:** `get_db` commits on success, rolls back on exception. Services call `session.flush()` internally. No commit in Repository or Service.
2. **Idempotency:** Single `idempotency_records` table with INSERT ON CONFLICT DO NOTHING RETURNING pattern. No idempotency_key on business tables.
3. **Optimistic locking:** `version` column on users, products, orders, tickets, refunds, reshipments.
4. **Monetary precision:** PostgreSQL `NUMERIC(12,2)` → Python `Decimal`. No `float`.
5. **Stock management:** Pre-check at order create (non-locking). Deduction at pay (SELECT FOR UPDATE).
6. **Partial refund = no order status change.** Only full refund → REFUNDED.
7. **No transient states:** No PROCESSING in tickets, no REFUNDING in orders, no refund_status enum.
8. **Lock ordering:** ticket → order → order_items (by id ASC) → products (by product_id ASC). Post-lock re-validation.
9. **Active ticket dedup:** Partial unique index with server-computed request_fingerprint.
10. **Transaction orchestration in Service layer** — Router never opens new DB tx.

---

## Known Limitations

1. No payment gateway — payment/refund are simulated status transitions
2. No EXCHANGE implementation beyond creating a NEEDS_REVIEW ticket
3. No config write API — after-sales configs set via seed script or direct DB
4. No approval_tasks table — NEEDS_REVIEW is a ticket status
5. No Agent, no LangGraph, no RAG, no Memory (Phase 03-05)
6. No email notifications
7. No Redis, no Kafka, no microservices (by design)

---

## Latest Commits

```
691e8c2 [Phase 02B] Completion report — 49 tests pass, ruff/mypy green, migration cycle verified
64a574b [Phase 02B] Repositories, services, schemas, API routes, and 16 tests
436e6ed [Phase 02B] Migration 003, models, enums, and rules layer
f6d9c17 [Phase 02B] Finalize after-sales backend implementation plan
5bbdf6b [Phase 02A] Fix request transaction persistence and test isolation
```

All commits pushed to GitHub.

---

## Next Task

**Phase 03 — Agent Tools** (planning not yet started).
See `tasks/active-phase.md` for current phase pointer.

---

## Start & Test Commands

```bash
# PostgreSQL
docker compose up -d db

# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Full check
ruff check app/ tests/
mypy --no-incremental app/ tests/
pytest -v

# Fresh test database
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
