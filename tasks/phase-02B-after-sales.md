# Phase 02B — After-sales Business Backend

## Phase Goals

Implement after-sales business entities: tickets, refunds, reshipments. Add refund/return-related order statuses and item flags. Build after-sales eligibility rules, refund calculation engine, and risk assessment. Implement corresponding APIs.

## Preconditions

- Phase 02A completed (Core Commerce Backend).
- All Phase 02A acceptance criteria met.

## Task Checklist

### 2B.1 Database Migration
- [ ] `alembic/versions/003_create_after_sales_tables.py`.
- [ ] ALTER TYPE order_status ADD VALUE 'REFUNDING', 'REFUNDED'.
- [ ] ALTER TABLE order_items ADD COLUMN is_refunded BOOLEAN DEFAULT FALSE.
- [ ] CREATE TYPE × 13 (intent_type, ticket_status, resolution_type, refund_type, refund_status, reshipment_status, approval_type, approval_status, session_status, message_role, memory_type, policy_category, policy_status).
- [ ] CREATE TABLE × 3 (after_sales_tickets, refund_records, reshipment_orders).
- [ ] Idempotency keys on tickets, refunds, reshipments.

### 2B.2 Models
- [ ] `AfterSalesTicket` — idempotency_key, version, intent, status, resolution_type.
- [ ] `RefundRecord` — idempotency_key, version, amount, type, status.
- [ ] `ReshipmentOrder` — idempotency_key, version, missing_items JSONB, status.

### 2B.3 Repositories
- [ ] `AfterSalesTicketRepository`.
- [ ] `RefundRepository`.
- [ ] `ReshipmentRepository`.

### 2B.4 Services
- [ ] `TicketService` — create with idempotency, list, update status.
- [ ] `RefundService` — create (transaction: refund + order status + audit), idempotency.
- [ ] `ReshipmentService` — create (transaction: reshipment + audit), idempotency.

### 2B.5 Rules Engine
- [ ] `rules/eligibility.py` — eligibility per intent type.
- [ ] `rules/refund_calculator.py` — deterministic refund amount.
- [ ] `rules/risk.py` — risk level assessment.

### 2B.6 API Endpoints
- [ ] Tickets: GET list, GET detail (customer); GET all, PATCH update (admin).
- [ ] Refunds: POST create (via ticket flow).
- [ ] Reshipments: POST create (via ticket flow).

### 2B.7 Testing
- [ ] Model constraint tests.
- [ ] Repository tests.
- [ ] Service tests (transaction, idempotency).
- [ ] API integration tests.
- [ ] Eligibility rule tests.
- [ ] Refund calculation tests.
- [ ] Risk assessment tests.

## Deferred from This Phase

- ApprovalTask model → Phase 06.
- Human-in-the-loop approval logic → Phase 06.
- Agent session/message/log/trace tables → Phase 03.

## Acceptance Criteria

- [ ] `alembic upgrade head` creates 3 new tables + extends order_status + order_items.
- [ ] `alembic downgrade -1` clean rollback.
- [ ] Ruff, mypy, pytest all pass.
- [ ] Ticket CRUD works.
- [ ] Refund creation is transactional.
- [ ] Duplicate refunds prevented.
- [ ] Invalid state transitions rejected.
- [ ] Audit logs for all state changes.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
