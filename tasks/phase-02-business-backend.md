# Phase 02 — Business Backend (总索引)

## Phase Goals

Implement the complete business logic layer in two sub-phases.

## Revision History

- **2026-07-13 (original):** Plan from Phase 00.
- **2026-07-13 (r1):** Added model creation, enum creation, auth, product API, seed data from Phase 01.
- **2026-07-13 (r2):** Split into Phase 02A (Core Commerce) and Phase 02B (After-sales).
- **2026-07-13 (r3):** Consistency corrections — INSERT ON CONFLICT idempotency, request_hash, expected_version, PAID cancel deferred, etc.
- **2026-07-13 (r4):** Phase 02A completed. Phase 02B fully designed with state machines, eligibility rules, refund calculation, API, test plan.
- **2026-07-14 (r5):** Phase 02B planning revision — 12 design corrections (partial refund Plan B, atomic refund no PROCESSING, requested_items/refund_items/missing_items JSONB, unified idempotency, cancel boundary, PROCESSING→NEEDS_REVIEW, agent_notes→operator_notes, PostgreSQL sequences, config scope, migration rollback assertions).
- **2026-07-14 (r6):** Phase 02B final fix — 9 targeted corrections (cumulative refund cap with shipping_refund_amount, lock ordering with post-lock re-validation, cross-key duplicate guard UNIQUE(ticket_id), reshipment logistics fields, remove ticket PROCESSING, remove refund_status enum, active ticket partial unique index with request_fingerprint, 13 API endpoints, 6-assertion downgrade).

## Sub-Phases

| Phase | Name | Status | Tables | Enums Added | Document |
|-------|------|--------|--------|-------------|----------|
| 02A | Core Commerce Backend | ✅ Complete | 8 | 5 | [phase-02A-core-commerce.md](phase-02A-core-commerce.md) |
| 02B | After-sales Business Backend | ⬜ Planning (v5) | 3 (+2 ALTER) | 5 (+1 ALTER) + 2 sequences | [phase-02B-after-sales.md](phase-02B-after-sales.md) |

## Phase 02A Summary

- 8 tables: users, products, orders, order_items, logistics_records, audit_logs, system_configs, idempotency_records
- 5 enums: user_role, risk_level, product_category, order_status, logistics_status
- 18 API endpoints, JWT auth with RBAC, order lifecycle (create→pay→ship→deliver→cancel)
- Idempotency: INSERT ON CONFLICT DO NOTHING RETURNING
- Optimistic locking via version column
- 33 self-contained tests, CI green

## Phase 02B Scope

- 3 new tables: after_sales_tickets, refund_records, reshipment_orders (no idempotency_key columns)
- 2 new sequences: ticket_number_seq, reshipment_number_seq
- 5 new enums: intent_type, ticket_status, resolution_type, refund_type, reshipment_status (no refund_status)
- ALTER order_status: add REFUNDED only
- ALTER order_items: add refunded_quantity, reshipped_quantity
- Cumulative refund cap: SUM(existing) + current ≤ paid_amount; shipping_refund_amount with cap ≤ shipping_fee
- Lock ordering: ticket → order → order_items → products; post-lock re-validation
- Cross-key duplicate guard: UNIQUE(ticket_id) on refund_records + reshipment_orders; mutual exclusion
- Active ticket dedup: partial unique index (order_id, intent, request_fingerprint) WHERE status IN ('APPROVED','NEEDS_REVIEW')
- Reshipment logistics: tracking_number, carrier, shipped_at, delivered_at
- 13 API endpoints (4 customer + 9 operator/admin)
- 6-assertion downgrade protection
- All deterministic code — no LLM, no Agent

## Entity Allocation

| Entity | Phase 02A | Phase 02B | Later |
|--------|-----------|-----------|-------|
| users, products, orders, order_items | ✅ (base) | ✅ (extended) | |
| logistics_records, audit_logs, system_configs | ✅ | | |
| idempotency_records | ✅ | ✅ (reused) | |
| after_sales_tickets, refund_records, reshipment_orders | | ✅ | |
| order_status: REFUNDING, REFUNDED | | ✅ | |
| order_items: refunded_quantity, reshipped_quantity | | ✅ | |
| approval_tasks | | | Phase 06 |
| agent_sessions, agent_messages, agent_tool_logs, agent_traces | | | Phase 03 |
| customer_memories | | | Phase 05 |
| policy_documents | | | Phase 04 |

## Completion Record

- **Phase 02A Started:** 2026-07-13
- **Phase 02A Completed:** 2026-07-13
- **Phase 02B Started:** TBD
- **Phase 02B Completed:** TBD
