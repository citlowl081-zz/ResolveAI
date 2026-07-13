# Phase 02 — Business Backend (总索引)

## Phase Goals

Implement the complete business logic layer. The original Phase 02 plan has been split into two sub-phases to ensure each can be independently tested, committed, and verified.

## Revision History

- **2026-07-13 (original):** Plan from Phase 00.
- **2026-07-13 (r1):** Added model creation, enum creation, auth, product API, seed data — moved from Phase 01.
- **2026-07-13 (r2):** Split into Phase 02A (Core Commerce) and Phase 02B (After-sales).
- **2026-07-13 (r3):** Consistency corrections — INSERT ON CONFLICT idempotency, VARCHAR CHECK status, request_hash spec, expected_version, PAID cancel deferred, duplicate product aggregation, logistics FOR UPDATE, NUMERIC(12,2)+Decimal, Phase 02B enum migration strategy.

## Sub-Phases

| Phase | Name | Status | Tables | Enums | Document |
|-------|------|--------|--------|-------|----------|
| 02A | Core Commerce Backend | ⬜ Pending | 8 | 5 | [phase-02A-core-commerce.md](phase-02A-core-commerce.md) |
| 02B | After-sales Business Backend | ⬜ Pending | 3 (+2 ALTER) | 6 (+1 ALTER) | [phase-02B-after-sales.md](phase-02B-after-sales.md) |

## Split Rationale

1. **Independent testability:** Phase 02A delivers a working e-commerce backend without after-sales logic.
2. **Incremental migration:** Each sub-phase has its own Alembic migration.
3. **Reduced risk:** Smaller phases mean fewer changes per commit, easier rollback.
4. **No empty tables:** Tables are created in the same phase as their business logic.
5. **Enum safety:** Phase 02B's order_status extension uses CREATE TYPE → CONVERT → DROP → RENAME pattern rather than ALTER TYPE ADD VALUE (which cannot be cleanly downgraded).

## Entity Allocation

| Entity | Phase 02A | Phase 02B | Later |
|--------|-----------|-----------|-------|
| users, products, orders, order_items | ✅ | | |
| logistics_records | ✅ | | |
| audit_logs, system_configs | ✅ | | |
| idempotency_records | ✅ | | |
| after_sales_tickets, refund_records, reshipment_orders | | ✅ | |
| order_status.REFUNDING, REFUNDED | | ✅ | |
| order_items.is_refunded | | ✅ | |
| PAID→CANCELLED (stock restore) | | ✅ | |
| approval_tasks | | | Phase 06 |
| agent_sessions, agent_messages | | | Phase 03 |
| agent_tool_logs, agent_traces | | | Phase 03 |
| customer_memories | | | Phase 05 |
| policy_documents | | | Phase 04 |

## Preconditions (Shared)

- Phase 01 completed.
- Test database available (PostgreSQL + pgvector).

## Completion Record

- **Phase 02A Started:** TBD
- **Phase 02A Completed:** TBD
- **Phase 02B Started:** TBD
- **Phase 02B Completed:** TBD
