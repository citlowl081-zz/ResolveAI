# Phase 02 — Business Backend (总索引)

## Phase Goals

Implement the complete business logic layer. The original Phase 02 plan has been split into two sub-phases to ensure each can be independently tested, committed, and verified.

## Revision History

- **2026-07-13 (original):** Plan from Phase 00.
- **2026-07-13 (revision 1):** Added model creation, enum creation, auth, product API, seed data, and business migration tasks moved from Phase 01.
- **2026-07-13 (revision 2):** Split into Phase 02A (Core Commerce) and Phase 02B (After-sales) per user direction. The split avoids implementing all 17 tables and complex after-sales logic in one phase.

## Sub-Phases

| Phase | Name | Status | Document |
|-------|------|--------|----------|
| 02A | Core Commerce Backend | ⬜ Pending | [phase-02A-core-commerce.md](phase-02A-core-commerce.md) |
| 02B | After-sales Business Backend | ⬜ Pending | [phase-02B-after-sales.md](phase-02B-after-sales.md) |

## Split Rationale

1. **Independent testability:** Phase 02A delivers a working e-commerce backend (auth, products, orders, logistics) without any after-sales logic. It can be tested end-to-end independently.
2. **Incremental migration:** Each sub-phase has its own Alembic migration. Tables are added incrementally rather than all at once.
3. **Reduced risk:** Smaller phases mean fewer changes per commit, easier rollback, and clearer acceptance criteria.
4. **No empty tables:** Tables are created in the same phase where their business logic is implemented. No forward-declaration of schema without corresponding code.

## What Went Where

| Original Phase 02 Task | → Phase 02A | → Phase 02B | → Later |
|------------------------|-------------|-------------|---------|
| Users, Products, Orders, OrderItems, Logistics models | ✅ | | |
| AuditLog, SystemConfig models | ✅ | | |
| IdempotencyRecord model | ✅ (added) | | |
| AfterSalesTicket, RefundRecord, ReshipmentOrder models | | ✅ | |
| ApprovalTask model | | | Phase 06 |
| AgentSession, AgentMessage models | | | Phase 03 |
| AgentToolLog, AgentTrace models | | | Phase 03 |
| CustomerMemory model | | | Phase 05 |
| PolicyDocument model | | | Phase 04 |
| Auth (register, login, JWT, RBAC) | ✅ | | |
| Product CRUD API | ✅ | | |
| Order lifecycle API (create/pay/ship/deliver/cancel) | ✅ | | |
| Logistics API | ✅ | | |
| Audit logging | ✅ | | |
| Seed data (users, products, orders) | ✅ | | |
| After-sales eligibility, refund calc, risk rules | | ✅ | |
| Ticket/Refund/Reshipment APIs | | ✅ | |
| 18 PostgreSQL enums | 5 of 18 | remaining | |

## Preconditions (Shared)

- Phase 01 completed (FastAPI app, DB infrastructure, health check, Alembic with pgvector, frontend scaffolds).
- Test database available (PostgreSQL + pgvector).
- All Phase 01 tests passing.

## Completion Record

- **Phase 02A Started:** TBD
- **Phase 02A Completed:** TBD
- **Phase 02B Started:** TBD
- **Phase 02B Completed:** TBD
