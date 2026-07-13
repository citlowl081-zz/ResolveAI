# Phase 02B — After-sales Business Backend

## Phase Goals

Implement after-sales business entities: tickets, refunds, reshipments. Add refund/return-related order statuses (REFUNDING, REFUNDED) and `order_items.is_refunded` column. Implement PAID order cancellation with stock restoration. Build after-sales eligibility rules, refund calculation engine, and risk assessment. Implement corresponding APIs.

## Revision History

- **2026-07-13 (v1):** Initial plan from Phase 02 split.
- **2026-07-13 (v2):** Added enum migration strategy (create-new-type→convert→drop-old→rename), PAID cancel logic moved from Phase 02A, 13 additional enums.

## Preconditions

- Phase 02A completed (Core Commerce Backend).
- All Phase 02A acceptance criteria met.

## Task Checklist

### 2B.1 Database Migration
- [ ] `alembic/versions/003_create_after_sales_tables.py`.
- [ ] **Enum migration strategy for order_status:**
  ```
  -- Upgrade:
  CREATE TYPE order_status_new AS ENUM (
    'PENDING_PAYMENT','PAID','SHIPPED','DELIVERED',
    'CANCELLED','REFUNDING','REFUNDED'
  );
  ALTER TABLE orders ALTER COLUMN status TYPE order_status_new
    USING status::text::order_status_new;
  DROP TYPE order_status;
  ALTER TYPE order_status_new RENAME TO order_status;

  -- Downgrade:
  CREATE TYPE order_status_old AS ENUM (
    'PENDING_PAYMENT','PAID','SHIPPED','DELIVERED','CANCELLED'
  );
  -- Assert no rows use REFUNDING/REFUNDED before proceeding
  ALTER TABLE orders ALTER COLUMN status TYPE order_status_old
    USING status::text::order_status_old;
  DROP TYPE order_status;
  ALTER TYPE order_status_old RENAME TO order_status;
  ```
- [ ] ALTER TABLE order_items ADD COLUMN is_refunded BOOLEAN DEFAULT FALSE.
- [ ] CREATE TYPE × 13 (intent_type, ticket_status, resolution_type, refund_type, refund_status, reshipment_status, approval_type, approval_status, session_status, message_role, memory_type, policy_category, policy_status).
- [ ] CREATE TABLE × 3 (after_sales_tickets, refund_records, reshipment_orders).
- [ ] Idempotency keys on tickets, refunds, reshipments.

### 2B.2 Models
- [ ] `AfterSalesTicket` — idempotency_key, version, intent, status, resolution_type.
- [ ] `RefundRecord` — idempotency_key, version, amount (NUMERIC(12,2)), type, status.
- [ ] `ReshipmentOrder` — idempotency_key, version, missing_items JSONB, status.

### 2B.3 Repositories
- [ ] `AfterSalesTicketRepository`.
- [ ] `RefundRepository`.
- [ ] `ReshipmentRepository`.

### 2B.4 Services
- [ ] `TicketService` — create with idempotency, list, update status.
- [ ] `RefundService` — create (transaction: refund + order status + audit), idempotency.
- [ ] `ReshipmentService` — create (transaction: reshipment + audit), idempotency.
- [ ] PAID order cancellation with stock restoration and refund logic.

### 2B.5 Rules Engine
- [ ] `rules/eligibility.py` — eligibility per intent type.
- [ ] `rules/refund_calculator.py` — deterministic refund amount (Decimal).
- [ ] `rules/risk.py` — risk level assessment.

### 2B.6 API Endpoints
- [ ] `POST /api/v1/orders/{id}/cancel` extended — now accepts PAID orders with stock restoration.
- [ ] Tickets: GET list, GET detail (customer); GET all, PATCH update (admin).
- [ ] Refunds: via ticket flow.
- [ ] Reshipments: via ticket flow.

### 2B.7 Testing
- [ ] Enum migration upgrade/downgrade cycle (order_status type replacement).
- [ ] Model constraint tests.
- [ ] Repository tests.
- [ ] Service tests (transaction, idempotency).
- [ ] API integration tests.
- [ ] PAID cancel with stock restoration.
- [ ] Eligibility rule tests.
- [ ] Refund calculation tests (Decimal precision).
- [ ] Risk assessment tests.

## Deferred from This Phase

- ApprovalTask model → Phase 06.
- Human-in-the-loop approval logic → Phase 06.
- Agent session/message/log/trace tables → Phase 03.
- Policy documents + RAG → Phase 04.
- Customer memories → Phase 05.

## Acceptance Criteria

- [ ] `alembic upgrade head` creates 3 tables + extends order_status (via type replacement) + adds is_refunded column + 13 enums.
- [ ] `alembic downgrade -1` clean rollback (order_status restored without REFUNDING/REFUNDED).
- [ ] Ruff, mypy, pytest all pass.
- [ ] Ticket CRUD works.
- [ ] Refund creation is transactional (Decimal amounts).
- [ ] Duplicate refunds prevented by idempotency.
- [ ] PAID cancel restores stock.
- [ ] Invalid state transitions rejected.
- [ ] Audit logs for all state changes.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
