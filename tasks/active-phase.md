# Active Phase

**Current Phase:** Phase 02B — After-sales Business Backend

**Status:** Final Planning Fix v5 (9-point correction, awaiting approval)

## What Phase 02B Covers

- 3 new tables: after_sales_tickets, refund_records, reshipment_orders (no idempotency_key columns)
- 2 PostgreSQL sequences: ticket_number_seq, reshipment_number_seq
- 5 new enums + order_status extension (REFUNDED only); refund_status enum removed
- order_items extended with refunded_quantity, reshipped_quantity
- requested_items, refund_items, missing_items JSONB with strict server-side validation
- request_fingerprint column with partial unique index for active ticket dedup
- Cumulative refund cap: SUM(existing) + current ≤ order.paid_amount
- shipping_refund_amount with cumulative cap ≤ order.shipping_fee
- Lock ordering: ticket→order→order_items→products; post-lock re-validation
- Cross-key duplicate guard: UNIQUE(ticket_id) on refund_records + reshipment_orders
- Reshipment logistics: tracking_number, carrier, shipped_at, delivered_at
- Ticket states: APPROVED/REJECTED/COMPLETED/CANCELLED/NEEDS_REVIEW (no PROCESSING)
- 13 API endpoints (4 customer + 9 operator/admin)
- 6-assertion downgrade protection; no silent data loss
- Transaction orchestration in Service layer only
- Full test coverage (42 tests, self-contained, no seed dependency)

## Previous Phase

Phase 02A completed on 2026-07-13. CI all green. See `reports/progress/phase-02A-report.md` (pending generation).

## Sub-Phase Documents

- [Phase 02A — Core Commerce Backend](phase-02A-core-commerce.md) ✅
- [Phase 02B — After-sales Business Backend](phase-02B-after-sales.md) ⬜ Pending
- [Phase 02 — Business Backend (Index)](phase-02-business-backend.md)
