# Phase 02 — Business Backend

## Phase Goals

Implement the complete business logic layer: repositories, services, and API endpoints for all business entities. This phase establishes the REST API that both the frontend and the agent tools will use.

## Preconditions

- Phase 01 completed (database models, migrations, auth working).
- Test database available.

## Task Checklist

### 2.1 Repository Layer
- [ ] `UserRepository` — CRUD, get by email, update risk level.
- [ ] `ProductRepository` — list with filters, get by id.
- [ ] `OrderRepository` — create, list by user, get by id, update status, optimistic locking.
- [ ] `OrderItemRepository` — list by order.
- [ ] `LogisticsRepository` — get by order, create, update status.
- [ ] `AfterSalesTicketRepository` — create, list by user/order, get by id, update status, idempotency check.
- [ ] `RefundRepository` — create, get by ticket/order, idempotency check.
- [ ] `ReshipmentRepository` — create, get by ticket/order, idempotency check.
- [ ] `ApprovalRepository` — create, list pending, get by id, update status.
- [ ] `PolicyRepository` — CRUD, list active, version management.
- [ ] `AuditLogRepository` — create, list with filters.
- [ ] `SystemConfigRepository` — get by key, set.

### 2.2 Service Layer
- [ ] `AuthService` — register (hash password, create user), login (verify, generate tokens), refresh token.
- [ ] `ProductService` — list (with pagination and filters), get detail.
- [ ] `OrderService` — place order (transaction: create order + order items), list, get detail, status transitions.
- [ ] `LogisticsService` — get logistics, update (simulate status progression).
- [ ] `TicketService` — create ticket (with idempotency), get, list, update status.
- [ ] `RefundService` — create refund (transaction: create refund + update order + log audit), idempotency guard.
- [ ] `ReshipmentService` — create reshipment (transaction: create reshipment + log audit), idempotency guard.
- [ ] `ApprovalService` — create approval task, process approval (approve/reject), resume agent session.
- [ ] `PolicyService` — CRUD with versioning, activate/deactivate.
- [ ] `AuditService` — log event, query with filters.

### 2.3 API Endpoints
- [ ] Auth: POST register, POST login, POST refresh, GET me.
- [ ] Products: GET list, GET detail.
- [ ] Orders: POST create, GET list (user's), GET detail.
- [ ] Logistics: GET by order.
- [ ] Tickets: GET list (user's), GET detail.
- [ ] Admin Orders: GET all, GET detail.
- [ ] Admin Tickets: GET all, PATCH update.
- [ ] Admin Policies: CRUD, PATCH status.
- [ ] Admin Config: GET all, PUT update.
- [ ] Admin Dashboard: aggregate metrics.

### 2.4 Business Rules Engine
- [ ] `rules/eligibility.py` — Check eligibility for each intent type.
- [ ] `rules/refund_calculator.py` — Calculate refund amounts (deduct coupon, handle partial).
- [ ] `rules/risk.py` — Assess risk level based on amount, user, product.
- [ ] `rules/state_transitions.py` — Validate legal status transitions.

### 2.5 Testing
- [ ] Repository tests (each method with real DB).
- [ ] Service tests (with transaction verification).
- [ ] API integration tests (all endpoints).
- [ ] Business rules unit tests.
- [ ] State transition validation tests.
- [ ] Idempotency tests.

## Acceptance Criteria

- [ ] All repositories pass tests.
- [ ] All services pass tests.
- [ ] All API endpoints pass integration tests.
- [ ] Refund creation is transactional (fail → no partial state).
- [ ] Duplicate refunds prevented by idempotency keys.
- [ ] Invalid state transitions rejected.
- [ ] Audit logs created for all state changes.
- [ ] Ruff, mypy, pytest all pass.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
