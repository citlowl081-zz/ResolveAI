# Active Phase

**Current Phase:** Phase 02A — Core Commerce Backend

**Started:** TBD  
**Target Completion:** TBD  
**Status:** Pending (awaiting final plan confirmation)

## What Phase 02A Covers

- 8 database tables: users, products, orders, order_items, logistics_records, audit_logs, system_configs, idempotency_records.
- 5 PostgreSQL enums: user_role, risk_level, product_category, order_status, logistics_status.
- JWT authentication (access + refresh tokens) with token_type enforcement.
- Role-based access control (CUSTOMER, OPERATOR, ADMIN).
- Product CRUD with pagination, filtering, and optimistic locking.
- Order lifecycle: create → pay → ship → deliver → cancel.
- Logistics tracking with idempotent event logging.
- In-transaction idempotency (PROCESSING/COMPLETED/FAILED state machine).
- Optimistic locking via version column on all mutable entities.
- Deterministic stock deduction with SELECT FOR UPDATE ordering.
- Audit logging with field-level sanitization.
- Idempotent seed data.

## What Phase 02A Does NOT Cover

- After-sales tickets, refunds, reshipments (→ Phase 02B).
- Agent, LangGraph, RAG, Memory, Approval (→ Phases 03–06).

## Previous Phase

Phase 01 completed on 2026-07-13. See `reports/progress/phase-01-foundation-report.md`.

## Sub-Phase Documents

- [Phase 02A — Core Commerce Backend](phase-02A-core-commerce.md)
- [Phase 02B — After-sales Business Backend](phase-02B-after-sales.md)
- [Phase 02 — Business Backend (Index)](phase-02-business-backend.md)
