# Changelog

All notable changes to the ResolveAI project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] — 2026-07-16

### Added
- AnthropicProvider `base_url` parameter for DeepSeek/Qwen Anthropic-compatible endpoints.
- `scripts/configure-deepseek.sh` — secure API key input (hidden + chmod 600).
- `scripts/check-secrets.py` — git-tracked files secret scanner.
- `backend/scripts/smoke_deepseek.py` — manual real-model smoke test (not in CI).
- 10 new 900-series policy documents based on official Chinese regulations:
  - POL-RET-901/902: 7-day no-reason returns and excluded products.
  - POL-REF-901/902: quality-issue refunds, refund timeline, shipping fees.
  - POL-EXC-901: exchanges and product category rules.
  - POL-LOG-901: logistics delay, loss, damage, and delivery disputes.
  - POL-RES-901: missing/wrong items and reshipment.
  - POL-RISK-901: high-value and multi-item human approval rules.
  - POL-SOP-901: no-policy-match escalation to human agents.
  - POL-GEN-901: data minimization and personal information protection.
- `docs/knowledge-base-source-report.md` — traceable source report for new policies.
- Playwright E2E configs for customer-web (8 specs) and admin-web (7 specs).
- `tests/integration/test_seed_idempotency.py` — double-seed data stability test.

### Changed
- `docker-compose.yml`: `LLM_BASE_URL` env var, policy ingestion at startup, health checks.
- `.env.example`: DeepSeek/qwen config examples, demo account env vars.
- Default mock provider setup runs with zero real API keys.
- `seed.py`: env-configured demo accounts, idempotent logistics records.

### Fixed
- Separated policy consultation from explicit after-sales action requests.
- Idempotent demo logistics seeding (stable tracking numbers on rerun).
- `print()` replaced with `logging.getLogger(__name__)` in `ingest_policies.py`.
- Memory metric naming: False-Write Avoidance Rate and False Write Rate separated.

### Diagnostics & Security
- `check-secrets.py` reports file path and rule name only, never prints secrets.
- `smoke_deepseek.py` redacts API key from error messages automatically.

### Validation
- 469 backend tests passed (0 failures).
- Customer Web build + lint passed.
- Admin Web build + lint passed.
- Docker compose: 4 services healthy/running.
- Customer Playwright E2E: 8/8 passed.
- Admin Playwright E2E: 7/7 passed.
- Secret scanner: no secrets detected in tracked files.

## [0.2.0] — 2026-07-14

### Added (Phase 02A — Core Commerce Backend)
- 8 SQLAlchemy models: User, Product, Order, OrderItem, LogisticsRecord, AuditLog, SystemConfig, IdempotencyRecord.
- 5 PostgreSQL enums: user_role, risk_level, product_category, order_status, logistics_status.
- Alembic migration bc03591cd96c (8 tables + 5 enums).
- 18 API endpoints: 4 auth, 4 products, 7 orders, 2 logistics, 1 admin.
- JWT authentication with access (30min) / refresh (7d) token type enforcement.
- Role-based access control: CUSTOMER, OPERATOR, ADMIN with server-side enforcement.
- Order lifecycle: create → pay → ship → deliver → cancel.
- In-transaction idempotency: INSERT ON CONFLICT DO NOTHING RETURNING pattern.
- Optimistic locking via version column on all mutating operations.
- SELECT FOR UPDATE with sorted product IDs for deadlock prevention.
- NUMERIC(12,2) → Decimal for all monetary values.
- Audit logging with field-level PII sanitization.
- 33 self-contained integration tests (no seed dependency).
- GitHub Actions CI all green.

### Added (Phase 02B — After-sales Business Backend)
- 3 new SQLAlchemy models: AfterSalesTicket, RefundRecord, ReshipmentOrder.
- 5 new enums: intent_type, ticket_status, resolution_type, refund_type, reshipment_status.
- order_status extended with REFUNDED.
- order_items extended with refunded_quantity, reshipped_quantity.
- 2 PostgreSQL sequences: ticket_number_seq, reshipment_number_seq.
- Alembic migration 003 (3 tables + 5 enums + 2 sequences + 6-assertion downgrade protection).
- 13 API endpoints: 4 customer + 9 operator/admin for after-sales.
- Eligibility rules engine: 7 reject codes, NEEDS_REVIEW triggers.
- Deterministic refund calculator: Decimal precision, cumulative cap, shipping fee cap.
- Lock ordering: ticket → order → order_items → products with post-lock re-validation.
- Cross-key duplicate guard: UNIQUE(ticket_id) constraints.
- Active ticket dedup: partial unique index with server-computed request_fingerprint.
- Reshipment lifecycle: create → ship → deliver → cancel with stock management.
- 16 new integration tests (49 total, all passing).
- GitHub Actions remote CI all green.

## [0.1.0] — 2026-07-13

### Added (Phase 01 — Project Foundation)
- FastAPI app factory with CORS, lifespan, and exception handlers.
- Pydantic Settings configuration (DATABASE_URL resolution, CORS origins).
- Unified API response envelope (APIResponse[T]) and Pagination schemas.
- Unified exception hierarchy (AppError + 6 typed subclasses).
- Structlog logging with RequestID middleware.
- Async SQLAlchemy engine, session factory, and declarative Base + TimestampMixin.
- GET /api/v1/health endpoint (application + database status).
- PostgreSQL 16 + pgvector 0.8.5 via Docker Compose (healthcheck verified).
- Alembic async configuration with pgvector extension migration.
- Multi-stage Python Dockerfile.
- Next.js 14 customer-web (React 18, TypeScript 5, Tailwind 3).
- Next.js 14 admin-web (same stack).
- 14 automated tests (11 unit + 3 integration), all passing.
- GitHub Actions CI pipeline (lint, typecheck, test, build for all projects).
- Portable Makefile (PYTHON/venv variables, all core targets).
- Backend: Ruff zero errors, Mypy strict zero errors.
- Frontend: ESLint zero errors, tsc --noEmit zero errors, next build successful.

### Deferred to Phase 02
- All 17 business SQLAlchemy models and 18 PostgreSQL enums.
- JWT authentication, password hashing, role-based access control.
- Product API, order API, business services and repositories.
- Seed data and business Alembic migration.

## [0.0.0] — 2026-07-13

### Added
- Project initialization and Phase 00 planning.
- Complete project documentation (README, AGENTS.md, CLAUDE.md).
- Design documents for architecture, database, API, agent, RAG, memory, security.
- Task tracking for all 10 phases (00–09).
- Environment variable template (.env.example).
- Makefile with common development commands.
- Directory structure for backend, frontend, data, docs, tasks, and reports.
