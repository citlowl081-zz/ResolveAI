# Phase 02 — Business Backend

## Phase Goals

Implement the complete business logic layer: SQLAlchemy models, Alembic migration, repositories, services, API endpoints, auth, and seed data. This phase establishes the REST API that both the frontend and the agent tools will use.

## Revision History

- **2026-07-13 (original):** Plan from Phase 00.
- **2026-07-13 (revision):** Added model creation, enum creation, auth, product API, seed data, and business migration tasks moved from Phase 01.

## Preconditions

- Phase 01 completed (FastAPI app, DB infrastructure, health check, Alembic with pgvector, frontend scaffolds).
- Test database available (PostgreSQL + pgvector).

## Task Checklist

### 2.0 SQLAlchemy Models & Enums (Moved from Phase 01)
- [ ] Define all 18 PostgreSQL enums (user_role, risk_level, product_category, order_status, logistics_status, intent_type, ticket_status, resolution_type, refund_type, refund_status, reshipment_status, approval_type, approval_status, session_status, message_role, memory_type, policy_category, policy_status).
- [ ] `User` model with role enum.
- [ ] `Product` model with category enum.
- [ ] `Order` model with status enum, version for optimistic locking.
- [ ] `OrderItem` model.
- [ ] `LogisticsRecord` model with JSONB events.
- [ ] `AfterSalesTicket` model with idempotency_key, version.
- [ ] `RefundRecord` model with idempotency_key, version.
- [ ] `ReshipmentOrder` model with idempotency_key, version.
- [ ] `ApprovalTask` model.
- [ ] `AgentSession` model with JSONB graph_state.
- [ ] `AgentMessage` model.
- [ ] `AgentToolLog` model.
- [ ] `AgentTrace` model.
- [ ] `CustomerMemory` model.
- [ ] `PolicyDocument` model with pgvector embedding column.
- [ ] `AuditLog` model.
- [ ] `SystemConfig` model.

### 2.0b Business Migration & Seed Data (Moved from Phase 01)
- [ ] Generate Alembic migration `002_create_business_tables.py` for all 17 tables + 18 enums.
- [ ] Test: `alembic upgrade head` + `alembic downgrade -1`.
- [ ] Implement `app/database/seed.py` — seed script.
- [ ] Create 3 test users (customer, operator, admin).
- [ ] Create 10 sample products across categories.
- [ ] Create 3 sample orders with various statuses.
- [ ] Seed data runs on first startup (idempotent).

### 2.0c Security Foundation (Moved from Phase 01)
- [ ] Implement `app/security/jwt.py` — JWT token generation and validation.
- [ ] Implement `app/security/password.py` — password hashing with bcrypt.
- [ ] Implement `app/security/dependencies.py` — role-based dependency injection.
- [ ] Implement `app/security/pii.py` — complete PII masking utilities.

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
