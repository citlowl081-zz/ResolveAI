# Phase 02A — Core Commerce Backend

## Phase Goals

Build a working e-commerce backend that runs independently without LLM or Agent. Covers users, auth, products, orders, logistics, audit logs, and idempotency — everything needed for a basic commerce flow through delivery.

## Revision History

- **2026-07-13 (v1):** Initial plan derived from Phase 02 split.
- **2026-07-13 (v2):** Engineering corrections — in-transaction idempotency, composite unique constraint, optimistic locking, logistics idempotency, system_config layered, audit field filtering, stock lock ordering.

## Preconditions

- Phase 01 completed (FastAPI app, DB infrastructure, health check, Alembic with pgvector, frontend scaffolds).
- Test database available (PostgreSQL + pgvector).

---

## Task Checklist

### 2A.1 Database Migration
- [ ] Create `alembic/versions/002_create_core_commerce_tables.py`.
- [ ] CREATE TYPE × 5 (user_role, risk_level, product_category, order_status, logistics_status).
- [ ] CREATE TABLE × 8 (users, products, orders, order_items, logistics_records, audit_logs, system_configs, idempotency_records).
- [ ] All indexes, FK constraints, CHECK constraints, UNIQUE constraints.
- [ ] Composite UNIQUE on idempotency_records: `UNIQUE(user_id, operation, idempotency_key)`.
- [ ] Test: `alembic upgrade head` + `alembic downgrade -1`.

### 2A.2 Enums
- [ ] `app/models/enums.py` — Python enum definitions for all 5 PostgreSQL enums.

### 2A.3 SQLAlchemy Models (8 tables)
- [ ] `User` — version column for optimistic locking.
- [ ] `Product` — version column for optimistic locking.
- [ ] `Order` — version column for optimistic locking.
- [ ] `OrderItem`.
- [ ] `LogisticsRecord`.
- [ ] `AuditLog` — changes column with field-level filtering.
- [ ] `SystemConfig`.
- [ ] `IdempotencyRecord` — status (PROCESSING/COMPLETED/FAILED), locked_at, completed_at, error_code.

### 2A.4 Security
- [ ] `app/security/password.py` — bcrypt hashing via passlib.
- [ ] `app/security/jwt.py` — create_access_token (type="access", 30min), create_refresh_token (type="refresh", 7d), decode/validate with token_type enforcement.
- [ ] `app/security/dependencies.py` — get_current_user (requires type="access"), get_current_user_from_refresh (requires type="refresh"), require_role().

### 2A.5 Repository Layer (9 repositories)
- [ ] `app/repositories/base.py` — BaseRepository with common CRUD.
- [ ] `UserRepository` — get_by_email, create, get_by_id.
- [ ] `ProductRepository` — list with filters/pagination, get_by_id, create, update (with version check), get_by_ids_for_update.
- [ ] `OrderRepository` — create, list_by_user, get_by_id, update_status (with version check).
- [ ] `OrderItemRepository` — create_batch, list_by_order.
- [ ] `LogisticsRepository` — get_by_order, create, append_event.
- [ ] `AuditLogRepository` — create with sanitized changes.
- [ ] `SystemConfigRepository` — get_by_key, set.
- [ ] `IdempotencyRepository` — acquire (insert or check PROCESSING/COMPLETED), complete, fail.

### 2A.6 Service Layer (7 services)
- [ ] `app/services/auth.py` — register, login, refresh, get_me.
- [ ] `app/services/product.py` — list (paginated + filter), get, create (ADMIN), update (ADMIN, with version check).
- [ ] `app/services/order.py` — create (no stock deduction, price from DB), pay (SELECT FOR UPDATE, stock deduction, transactional), cancel (PENDING_PAYMENT→no stock; PAID→restore stock), ship (create logistics, transition), deliver (transition + logistics sync).
- [ ] `app/services/logistics.py` — get_by_order, add_event (idempotent via Idempotency-Key).
- [ ] `app/services/audit.py` — log with field-level sanitization.
- [ ] `app/services/idempotency.py` — acquire key (in-transaction), complete, handle conflicts.
- [ ] `app/services/system_config.py` — get, set (ADMIN).

### 2A.7 Rules Engine
- [ ] `app/rules/state_transitions.py` — allowed_transitions dict, validate_transition().

### 2A.8 API Endpoints (18 endpoints)

#### Auth
- [ ] `POST /api/v1/auth/register` — public.
- [ ] `POST /api/v1/auth/login` — public.
- [ ] `POST /api/v1/auth/refresh` — requires Refresh Token (type="refresh").
- [ ] `GET /api/v1/auth/me` — requires Access Token (type="access").

#### Products
- [ ] `GET /api/v1/products` — public, paginated, filterable by name/category.
- [ ] `GET /api/v1/products/{id}` — public.
- [ ] `POST /api/v1/products` — ADMIN only.
- [ ] `PATCH /api/v1/products/{id}` — ADMIN only, optimistic locking via version.

#### Orders
- [ ] `POST /api/v1/orders` — CUSTOMER, Idempotency-Key required. Items only: [{product_id, quantity}]. Price from DB.
- [ ] `GET /api/v1/orders` — CUSTOMER, own orders only.
- [ ] `GET /api/v1/orders/{id}` — owner/ADMIN/OPERATOR.
- [ ] `POST /api/v1/orders/{id}/pay` — owner, Idempotency-Key required. SELECT FOR UPDATE, stock deduction, version check.
- [ ] `POST /api/v1/orders/{id}/cancel` — owner/ADMIN, Idempotency-Key required. Stock restore if PAID.
- [ ] `POST /api/v1/orders/{id}/ship` — ADMIN/OPERATOR, Idempotency-Key required. Creates logistics.
- [ ] `POST /api/v1/orders/{id}/deliver` — ADMIN/OPERATOR, Idempotency-Key required. Syncs logistics.

#### Logistics
- [ ] `GET /api/v1/orders/{id}/logistics` — owner/ADMIN/OPERATOR.
- [ ] `POST /api/v1/orders/{id}/logistics/events` — ADMIN/OPERATOR, Idempotency-Key required.

#### Admin
- [ ] `GET /api/v1/admin/config` — ADMIN only.

### 2A.9 Seed Data
- [ ] `app/database/seed.py` — idempotent via ON CONFLICT / get_or_create.
- [ ] 1 ADMIN, 1 OPERATOR, 3 CUSTOMER users.
- [ ] 10 products across categories.
- [ ] Orders in various statuses with logistics.

### 2A.10 Idempotency (In-Transaction Design)

**Table: `idempotency_records`**
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK→users, NOT NULL | |
| operation | VARCHAR(50), NOT NULL | e.g., "order_create", "order_pay" |
| idempotency_key | VARCHAR(100), NOT NULL | From Idempotency-Key header |
| request_hash | VARCHAR(64), NOT NULL | SHA-256 of request body |
| status | idempotency_status ENUM, NOT NULL | PROCESSING, COMPLETED, FAILED |
| response_status | INTEGER | HTTP status of completed request |
| response_body | JSONB | Cached response |
| resource_id | UUID | Created/affected resource |
| error_code | VARCHAR(50) | Error code if FAILED |
| locked_at | TIMESTAMPTZ | When PROCESSING started |
| completed_at | TIMESTAMPTZ | When COMPLETED or FAILED |
| expires_at | TIMESTAMPTZ, NOT NULL | TTL (default 24h) |
| created_at | TIMESTAMPTZ, NOT NULL | |

**Unique constraint:** `UNIQUE(user_id, operation, idempotency_key)`

**Transaction flow:**
```
1. BEGIN TRANSACTION
2. SELECT ... FROM idempotency_records
   WHERE user_id=? AND operation=? AND idempotency_key=?
   AND (expires_at IS NULL OR expires_at > NOW())
   FOR UPDATE
3a. Found COMPLETED + same hash → return cached response, COMMIT
3b. Found COMPLETED + different hash → raise 409, ROLLBACK
3c. Found PROCESSING + not expired → raise 409 (request in progress), ROLLBACK
3d. Found PROCESSING + expired (>30s locked_at) → treat as stale, continue
3e. Found FAILED → allow retry, continue
3f. Not found → INSERT PROCESSING record, continue
4. Execute business operation
5. On success: UPDATE status=COMPLETED, response_status, response_body, resource_id, completed_at=NOW()
6. On failure: UPDATE status=FAILED, error_code (or ROLLBACK entire tx)
7. COMMIT
```

**Idempotency-protected endpoints (7):**
| Endpoint | Operation | Idempotency-Key |
|---------|-----------|-----------------|
| POST /api/v1/orders | order_create | Required |
| POST /api/v1/orders/{id}/pay | order_pay | Required |
| POST /api/v1/orders/{id}/cancel | order_cancel | Required |
| POST /api/v1/orders/{id}/ship | order_ship | Required |
| POST /api/v1/orders/{id}/deliver | order_deliver | Required |
| POST /api/v1/orders/{id}/logistics/events | logistics_event | Required |
| POST /api/v1/products | product_create | Optional (幂等创建) |

### 2A.11 Optimistic Locking (version field)

**Applies to:**
- PATCH /api/v1/products/{id} — `WHERE id=? AND version=?`
- POST /api/v1/orders/{id}/pay — `WHERE id=? AND version=?`
- POST /api/v1/orders/{id}/cancel — `WHERE id=? AND version=?`
- POST /api/v1/orders/{id}/ship — `WHERE id=? AND version=?`
- POST /api/v1/orders/{id}/deliver — `WHERE id=? AND version=?`

**Pattern:**
```sql
UPDATE orders
SET status='PAID', paid_at=NOW(), version = version + 1
WHERE id = :id AND version = :expected_version
RETURNING version
```
No row returned → raise 409 CONCURRENT_MODIFICATION.

### 2A.12 Product Lock Ordering

When paying or cancelling (which locks multiple products):
1. Sort product IDs ascending.
2. SELECT ... FOR UPDATE in ascending order.
3. This prevents deadlocks from inconsistent lock ordering.

### 2A.13 Audit Log Sanitization

`audit_logs.changes` must NOT contain:
- `hashed_password`
- `password`
- `access_token`
- `refresh_token`
- Full phone numbers (mask to `138****5678`)
- Full addresses (mask to `北京市****`)
- JWT content
- `authorization` header values

**Filtering:** Field-level allowlist on write. Only explicitly whitelisted fields are stored in `changes`.

**Transaction boundary:** Audit log INSERT is in the same transaction as the business operation. If the business tx rolls back, the audit entry is also discarded.

### 2A.14 Stock Check at Order Creation

- Non-locking pre-check: `requested_quantity <= current_stock`.
- Used for early feedback only — does NOT reserve stock.
- Payment step re-validates under SELECT FOR UPDATE.
- If payment finds insufficient stock → 422, order stays PENDING_PAYMENT.

---

## Testing Requirements

- [ ] Enum definition tests.
- [ ] State transition matrix (all legal + illegal transitions).
- [ ] JWT create/validate, token_type enforcement.
- [ ] Password hash + PII masking.
- [ ] All schema validation + edge cases.
- [ ] All 9 repositories — CRUD + version check + lock ordering.
- [ ] All 7 services — transaction boundaries, rollback, stock correctness.
- [ ] Auth API: register→login→refresh→me full chain + wrong token type.
- [ ] Products API: pagination, filter, ADMIN CRUD, permission denial.
- [ ] Orders API: full lifecycle create→pay→ship→deliver + cancel variants.
- [ ] RBAC: cross-user access, anonymous, role escalation attempts.
- [ ] Audit: all mutating operations logged, sensitive fields absent.
- [ ] Idempotency: replay, different body conflict, concurrent pay, concurrent ship.
- [ ] Stock: deduction atomicity, restore on cancel, oversell rejection.
- [ ] Seed: idempotent re-run, correct counts.

**Coverage requirements (not count targets):**
- All core state transitions covered.
- All role permissions covered.
- Critical transaction success and rollback covered.
- Duplicate requests and idempotency conflicts covered.
- Stock deduction and restoration covered.
- Cross-user access violations covered.
- Token type errors covered.
- Audit log sanitization covered.

---

## Acceptance Criteria

- [ ] `alembic upgrade head` creates 8 tables + 5 enums.
- [ ] `alembic downgrade -1` clean rollback.
- [ ] `ruff check` zero errors.
- [ ] `mypy` zero errors.
- [ ] `pytest -v` all passing (real PostgreSQL).
- [ ] Register → login → access protected endpoint.
- [ ] Refresh token works; wrong token type rejected.
- [ ] RBAC: CUSTOMER cannot create products; cannot read other's orders.
- [ ] Product CRUD works with version-based optimistic locking.
- [ ] Order lifecycle: create → pay → ship → deliver.
- [ ] Cancel PENDING_PAYMENT order (no stock impact).
- [ ] Cancel PAID order (stock restored).
- [ ] Ship/Deliver after PAID only; illegal transitions get 409.
- [ ] Stock never goes negative (SELECT FOR UPDATE + CHECK constraint).
- [ ] Concurrent modification returns 409 (version mismatch).
- [ ] Idempotency: replay returns same result; different body returns 409.
- [ ] Idempotency: concurrent pay on same order → one succeeds, other gets 409.
- [ ] Audit logs created for pay/ship/deliver/cancel/product change.
- [ ] Audit logs contain no passwords, tokens, full phone, or full address.
- [ ] Seed script idempotent on re-run.
- [ ] GitHub Actions CI passes.

---

## Known Limitations

- **No server-side Refresh Token revocation.** Short Access Token TTL (30 min) partially mitigates. Full revocation deferred.
- **No payment_gateway table.** Payment is simulated by status transition only.
- **No shopping cart.** Direct order creation only.
- **No inventory reservation.** Stock checked at create, deducted at pay.

---

## Deferred to Phase 02B

- after_sales_tickets, refund_records, reshipment_orders tables.
- order_items.is_refunded column.
- order_status.REFUNDING, REFUNDED values (added via new migration).
- Refund calculation, after-sales eligibility rules.
- Ticket/Refund/Reshipment APIs.

---

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
- **Reviewer:** Self
