# Phase 02A — Core Commerce Backend

## Phase Goals

Build a working e-commerce backend that runs independently without LLM or Agent. Covers users, auth, products, orders, logistics, audit logs, and idempotency — everything needed for a basic commerce flow through delivery.

## Revision History

- **2026-07-13 (v1):** Initial plan derived from Phase 02 split.
- **2026-07-13 (v2):** Engineering corrections — in-transaction idempotency, composite unique constraint, optimistic locking, logistics idempotency, system_config layered, audit field filtering, stock lock ordering.
- **2026-07-13 (v3):** Consistency corrections — INSERT ON CONFLICT flow, remove FAILED status, VARCHAR CHECK for idempotency status (5 enums only), request_hash specification, expected_version in request schemas, PAID cancel deferred to Phase 02B, duplicate product aggregation, logistics FOR UPDATE, NUMERIC(12,2) + Decimal, Phase 02B enum migration strategy.

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
- [ ] `UNIQUE(order_id, product_id)` on order_items to enforce aggregation.
- [ ] Composite UNIQUE on idempotency_records: `UNIQUE(user_id, operation, idempotency_key)`.
- [ ] `idempotency_records.status` is `VARCHAR(20) NOT NULL CHECK (status IN ('PROCESSING', 'COMPLETED'))`.
- [ ] Test: `alembic upgrade head` + `alembic downgrade -1`.

### 2A.2 Enums
- [ ] `app/models/enums.py` — Python enum definitions for exactly 5 PostgreSQL enums.

### 2A.3 SQLAlchemy Models (8 tables)
- [ ] `User` — version column for optimistic locking.
- [ ] `Product` — version column for optimistic locking.
- [ ] `Order` — version column for optimistic locking.
- [ ] `OrderItem` — product_name/unit_price snapshots; `UNIQUE(order_id, product_id)`.
- [ ] `LogisticsRecord` — events JSONB.
- [ ] `AuditLog` — changes JSONB with field-level allowlist sanitization.
- [ ] `SystemConfig`.
- [ ] `IdempotencyRecord` — status VARCHAR(20) CHECK (PROCESSING/COMPLETED), request_hash VARCHAR(64), locked_at, completed_at, expires_at, updated_at.

### 2A.4 Security
- [ ] `app/security/password.py` — bcrypt hashing via passlib.
- [ ] `app/security/jwt.py` — create_access_token (type="access", 30min), create_refresh_token (type="refresh", 7d), decode/validate with token_type enforcement. Claims: `jti`, `iat`, `exp`, `sub`, `role`, `type`.
- [ ] `app/security/dependencies.py` — `get_current_user` (requires type="access"), `get_current_user_from_refresh` (requires type="refresh"), `require_role()`.

### 2A.5 Repository Layer (9 repositories)
- [ ] `app/repositories/base.py` — BaseRepository with common CRUD.
- [ ] `UserRepository` — get_by_email, create, get_by_id.
- [ ] `ProductRepository` — list with filters/pagination, get_by_id, create, update (version check), get_by_ids_for_update (sorted ascending).
- [ ] `OrderRepository` — create, list_by_user, get_by_id, update_with_version.
- [ ] `OrderItemRepository` — create_batch (aggregated), list_by_order.
- [ ] `LogisticsRepository` — get_by_order_for_update (SELECT FOR UPDATE), create, append_event.
- [ ] `AuditLogRepository` — create with sanitized changes.
- [ ] `SystemConfigRepository` — get_by_key, set.
- [ ] `IdempotencyRepository` — acquire_or_check (INSERT ON CONFLICT DO NOTHING RETURNING), complete.

### 2A.6 Service Layer (7 services)
- [ ] `app/services/auth.py` — register, login, refresh, get_me.
- [ ] `app/services/product.py` — list (paginated + filter), get, create (ADMIN), update (ADMIN, version check).
- [ ] `app/services/order.py` — create (aggregate duplicates, no stock deduction, price from DB), pay (SELECT FOR UPDATE, stock deduction, transactional, version check), cancel (PENDING_PAYMENT only, no stock impact), ship (create logistics, version check), deliver (version check, logistics sync).
- [ ] `app/services/logistics.py` — get_by_order, add_event (idempotent, SELECT FOR UPDATE on logistics row).
- [ ] `app/services/audit.py` — log with field-level allowlist sanitization.
- [ ] `app/services/idempotency.py` — acquire via INSERT ON CONFLICT, complete, handle conflicts.
- [ ] `app/services/system_config.py` — get, set (ADMIN).

### 2A.7 Rules Engine
- [ ] `app/rules/state_transitions.py` — allowed_transitions dict, validate_transition().

### 2A.8 API Endpoints (17 endpoints)

#### Auth (4)
- [ ] `POST /api/v1/auth/register` — public.
- [ ] `POST /api/v1/auth/login` — public.
- [ ] `POST /api/v1/auth/refresh` — requires Refresh Token (type="refresh").
- [ ] `GET /api/v1/auth/me` — requires Access Token (type="access").

#### Products (4)
- [ ] `GET /api/v1/products` — public, paginated, filterable by name/category.
- [ ] `GET /api/v1/products/{id}` — public.
- [ ] `POST /api/v1/products` — ADMIN only.
- [ ] `PATCH /api/v1/products/{id}` — ADMIN only. Body requires `expected_version`. Returns `version`.

#### Orders (6)
- [ ] `POST /api/v1/orders` — CUSTOMER. Idempotency-Key required. Body: `{items: [{product_id, quantity}]}`. Duplicate product_ids aggregated. Prices from DB. No client-submitted amounts. Returns order with server-computed total.
- [ ] `GET /api/v1/orders` — CUSTOMER, own orders only.
- [ ] `GET /api/v1/orders/{id}` — owner/ADMIN/OPERATOR.
- [ ] `POST /api/v1/orders/{id}/pay` — owner. Idempotency-Key required. Body requires `expected_version`. SELECT FOR UPDATE with sorted product IDs. Stock deduction. Returns updated `version`.
- [ ] `POST /api/v1/orders/{id}/cancel` — owner/ADMIN. Idempotency-Key required. Body requires `expected_version`. **Only PENDING_PAYMENT allowed.** PAID/SHIPPED/DELIVERED → 409 (use after-sales flow). Returns updated `version`.
- [ ] `POST /api/v1/orders/{id}/ship` — ADMIN/OPERATOR. Idempotency-Key required. Body requires `expected_version`. Creates logistics record. Returns updated `version`.
- [ ] `POST /api/v1/orders/{id}/deliver` — ADMIN/OPERATOR. Idempotency-Key required. Body requires `expected_version`. Syncs logistics status. Returns updated `version`.

#### Logistics (2)
- [ ] `GET /api/v1/orders/{id}/logistics` — owner/ADMIN/OPERATOR.
- [ ] `POST /api/v1/orders/{id}/logistics/events` — ADMIN/OPERATOR. Idempotency-Key required. SELECT FOR UPDATE on logistics row before appending events.

#### Admin (1)
- [ ] `GET /api/v1/admin/config` — ADMIN only. Via SystemConfigService → SystemConfigRepository.

### 2A.9 Seed Data
- [ ] `app/database/seed.py` — idempotent via ON CONFLICT / get_or_create.
- [ ] 1 ADMIN, 1 OPERATOR, 3 CUSTOMER users.
- [ ] 10 products across categories.
- [ ] Orders in PENDING_PAYMENT, PAID, SHIPPED, DELIVERED statuses with logistics.

---

### 2A.10 Idempotency (INSERT ON CONFLICT DO NOTHING RETURNING)

**Table: `idempotency_records`**

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK, DEFAULT gen_random_uuid() | |
| user_id | UUID FK→users, NOT NULL | |
| operation | VARCHAR(50), NOT NULL | e.g. "order_create", "order_pay" |
| idempotency_key | VARCHAR(100), NOT NULL | From `Idempotency-Key` header |
| request_hash | VARCHAR(64), NOT NULL | SHA-256 of canonical request |
| status | VARCHAR(20), NOT NULL | CHECK (status IN ('PROCESSING','COMPLETED')) |
| response_status | INTEGER | HTTP status of completed request |
| response_body | JSONB | Cached API response |
| resource_id | UUID | Created/affected resource |
| locked_at | TIMESTAMPTZ | When PROCESSING began |
| completed_at | TIMESTAMPTZ | When COMPLETED |
| expires_at | TIMESTAMPTZ, NOT NULL | TTL, default NOW()+24h |
| created_at | TIMESTAMPTZ, NOT NULL | |
| updated_at | TIMESTAMPTZ, NOT NULL | |

**Unique constraint:** `UNIQUE(user_id, operation, idempotency_key)`

**No FAILED status.** Business failure → entire transaction rolls back, including the PROCESSING idempotency record. No persistent FAILED row. Client retries find no record and re-enter the acquire path.

**Transaction flow (INSERT ON CONFLICT DO NOTHING RETURNING):**

```
1. BEGIN TRANSACTION

2. Compute request_hash = SHA256(
     "METHOD|/api/v1/path/{param}|path_param=value|?query=value|{canonical_json_body}"
   )

3. INSERT INTO idempotency_records
     (user_id, operation, idempotency_key, request_hash, status, locked_at, expires_at)
   VALUES
     (:uid, :op, :key, :hash, 'PROCESSING', NOW(), NOW() + INTERVAL '24 hours')
   ON CONFLICT (user_id, operation, idempotency_key) DO NOTHING
   RETURNING id, status, request_hash, expires_at

4a. A row was RETURNED (我们插入了):
    - This request acquired the slot.
    - Proceed to execute business operation (step 5).

4b. No row returned (CONFLICT, another request exists):
    - SELECT id, status, request_hash, expires_at
      FROM idempotency_records
      WHERE user_id=:uid AND operation=:op AND idempotency_key=:key
      FOR UPDATE  ← blocks until the holder commits or rolls back

    - If status = 'COMPLETED' AND request_hash matches:
        → Return cached response_status + response_body. COMMIT.

    - If status = 'COMPLETED' AND request_hash differs:
        → 409 IDEMPOTENCY_CONFLICT. ROLLBACK.

    - If status = 'PROCESSING' AND expires_at > NOW():
        → 409 (another request is currently processing). ROLLBACK.

    - If status = 'PROCESSING' AND expires_at <= NOW() (expired):
        → UPDATE idempotency_records
          SET request_hash=:hash, status='PROCESSING',
              locked_at=NOW(), expires_at=NOW()+INTERVAL '24 hours'
          WHERE id=:existing_id
        → Proceed to execute business operation (step 5).

5. Execute business operation (stock deduction, order update, etc.)

6. On business success:
     UPDATE idempotency_records
     SET status='COMPLETED', response_status=:code, response_body=:body,
         resource_id=:rid, completed_at=NOW(), updated_at=NOW()
     WHERE id=:idempotent_row_id

7. COMMIT (or ROLLBACK on any error — idempotency record rolls back with tx)
```

**Concurrent correctness guarantee:** The INSERT ON CONFLICT atomically determines the winner. Losers block on FOR UPDATE until the winner commits or rolls back. Upon unblocking, losers see COMPLETED and return the cached result.

**request_hash specification:**

```
hash_input = "|".join([
    http_method,                          # "POST"
    normalized_path,                      # "/api/v1/orders/{order_id}/pay"
    canonical_path_params,                # "order_id=uuid-value"
    canonical_query_params,               # "" or "?key1=val1&key2=val2" (sorted)
    canonical_json_body,                  # sorted keys, no whitespace
])

request_hash = SHA256(hash_input)
```

**Idempotency-protected endpoints (7):**

| Endpoint | Operation | Key Required |
|---------|-----------|-------------|
| POST /api/v1/orders | order_create | Required |
| POST /api/v1/orders/{id}/pay | order_pay | Required |
| POST /api/v1/orders/{id}/cancel | order_cancel | Required |
| POST /api/v1/orders/{id}/ship | order_ship | Required |
| POST /api/v1/orders/{id}/deliver | order_deliver | Required |
| POST /api/v1/orders/{id}/logistics/events | logistics_event | Required |
| POST /api/v1/products | product_create | Optional |

---

### 2A.11 Optimistic Locking (version field + expected_version)

**Request schemas must include `expected_version`:**

| Endpoint | Body field |
|----------|-----------|
| PATCH /api/v1/products/{id} | `expected_version: int` |
| POST /api/v1/orders/{id}/pay | `expected_version: int` |
| POST /api/v1/orders/{id}/cancel | `expected_version: int` |
| POST /api/v1/orders/{id}/ship | `expected_version: int` |
| POST /api/v1/orders/{id}/deliver | `expected_version: int` |

**Response includes updated `version`.**

**SQL pattern:**
```sql
UPDATE orders
SET status = 'PAID', paid_at = NOW(), version = version + 1
WHERE id = :id AND version = :expected_version
RETURNING version
```
No row returned → `409 CONCURRENT_MODIFICATION`.

---

### 2A.12 Product Lock Ordering

Paying locks multiple products. To prevent deadlocks:
1. Sort product IDs ascending.
2. `SELECT ... FROM products WHERE id IN (...) ORDER BY id FOR UPDATE`.
3. All code paths that lock multiple products use this same ordering.

---

### 2A.13 Duplicate Product Aggregation

Order creation request may include the same `product_id` multiple times.

**Pre-processing before creating order:**
1. Group items by `product_id`.
2. Sum quantities: `total_qty = sum(q for q in items_with_same_product_id)`.
3. Use a single `order_item` row with the aggregated quantity.

**Enforced by:** `UNIQUE(order_id, product_id)` on `order_items`.

**Applies to:** stock pre-check, price lookup, order_item creation, payment stock deduction — all use aggregated quantities.

---

### 2A.14 Logistics JSONB Concurrency

`logistics_records.events` is a JSONB array. Appending events concurrently can cause lost updates.

**Append event flow:**
```
1. BEGIN TRANSACTION
2. SELECT * FROM logistics_records
   WHERE order_id = :order_id
   FOR UPDATE        ← row-level lock prevents concurrent overwrite
3. Append new event to events JSONB array in application code
4. UPDATE logistics_records SET events = :new_events, updated_at = NOW()
5. COMMIT
```

Different `Idempotency-Key` values produce different events — idempotency alone cannot prevent JSONB overwrites. This must be protected by row-level locking.

---

### 2A.15 Monetary Precision

**Database:**
```sql
total_amount   NUMERIC(12, 2) NOT NULL
paid_amount    NUMERIC(12, 2) DEFAULT 0
discount_amount NUMERIC(12, 2) DEFAULT 0
shipping_fee   NUMERIC(12, 2) DEFAULT 0
price          NUMERIC(12, 2) NOT NULL CHECK (price > 0)
unit_price     NUMERIC(12, 2) NOT NULL
subtotal       NUMERIC(12, 2) NOT NULL
```

**Python:** `Decimal` from the `decimal` module. All arithmetic uses `quantize(Decimal('0.01'))`.

**Prohibited:**
- `float` for any monetary value.
- Client-submitted `total_amount`, `paid_amount`, `discount_amount`, `price`.
- Coupon logic in Phase 02A (`discount_amount` fixed at 0, `coupon_code` fixed at NULL).

**Server-computed:** `total_amount = sum(item.subtotal) + shipping_fee - discount_amount`.

---

### 2A.16 Stock Check at Order Creation

- Non-locking pre-check: `requested_quantity <= current_stock` (per aggregated product).
- Early feedback only — does NOT reserve stock.
- Payment step re-validates under `SELECT FOR UPDATE`.
- Payment finds insufficient stock → 422, order stays PENDING_PAYMENT.
- No stock deduction at order creation.

---

### 2A.17 Audit Log Sanitization

**Whitelist (fields allowed in `changes` JSONB):**

| Entity | Allowed fields |
|--------|---------------|
| products | `name`, `description`, `price`, `stock`, `category`, `is_active` |
| orders | `status`, `paid_amount`, `total_amount`, `shipping_fee`, `cancel_reason` |
| logistics | `tracking_number`, `carrier`, `status`, `current_location` |

**Blacklist (never stored in `changes`):**
`hashed_password`, `password`, `access_token`, `refresh_token`, full JWT, `authorization` header, full `phone` (→ `138****5678`), full `shipping_address` (→ `北京市****`), `email` (→ `u***r@example.com`).

**Transaction boundary:** audit INSERT in the same transaction as business UPDATE. Rollback discards both.

---

## Testing Requirements

- [ ] Enum definition tests (5 enums).
- [ ] State transition matrix (all legal + illegal, including PAID→cancel rejection).
- [ ] JWT create/validate, token_type enforcement, wrong type rejection.
- [ ] Password hash + PII masking.
- [ ] All schema validation, including expected_version fields.
- [ ] All 9 repositories — CRUD, version check, lock ordering, aggregation.
- [ ] All 7 services — transaction boundaries, rollback, stock, monetary precision.
- [ ] Auth API: register→login→refresh→me + wrong token type on each endpoint.
- [ ] Products API: pagination, filter, ADMIN CRUD, permission denial, version conflict.
- [ ] Orders API: full lifecycle create→pay→ship→deliver, PAID-cancel rejection.
- [ ] Duplicate product aggregation: same product_id ×3 + ×2 → 1 row with qty=5.
- [ ] RBAC: cross-user access, anonymous, role escalation attempts.
- [ ] Audit: all mutating operations logged, sensitive fields absent, tx-bound.
- [ ] Idempotency: replay returns cached; different body→409; concurrent pay→one wins.
- [ ] Stock: deduction atomicity, oversell rejection, FOR UPDATE ordering.
- [ ] Logistics: concurrent event append under FOR UPDATE (two different keys, no lost events).
- [ ] Monetary: Decimal precision, client price tampering rejected.
- [ ] Seed: idempotent re-run, correct counts.

**Coverage requirements (not count targets):**
- All core state transitions covered.
- All role permissions covered.
- Critical transaction success and rollback covered.
- Duplicate requests and idempotency conflicts covered.
- Concurrent idempotency (INSERT ON CONFLICT) covered.
- Stock deduction covered; stock restoration deferred to Phase 02B.
- Cross-user access violations covered.
- Token type errors covered.
- Audit log sanitization covered.
- Monetary precision covered.
- Logistics JSONB concurrency covered.

---

## Acceptance Criteria

- [ ] `alembic upgrade head` creates 8 tables + 5 enums.
- [ ] `alembic downgrade -1` clean rollback.
- [ ] `ruff check` zero errors.
- [ ] `mypy` zero errors.
- [ ] `pytest -v` all passing (real PostgreSQL).
- [ ] Register → login → access protected endpoint.
- [ ] Refresh token works; wrong token type rejected (both directions).
- [ ] RBAC: CUSTOMER cannot create products; cannot read other's orders.
- [ ] Product CRUD with version-based optimistic locking; 409 on version mismatch.
- [ ] Order lifecycle: create → pay → ship → deliver.
- [ ] Cancel PENDING_PAYMENT → CANCELLED (no stock impact).
- [ ] Cancel PAID/SHIPPED/DELIVERED → 409 (use after-sales).
- [ ] Illegal state transitions → 409.
- [ ] Stock never negative (SELECT FOR UPDATE + CHECK constraint + transaction).
- [ ] Duplicate product_ids in order request aggregated into single order_item.
- [ ] UNIQUE(order_id, product_id) enforced.
- [ ] All amounts NUMERIC(12,2); client cannot set price/total/discount.
- [ ] Idempotency: replay returns cached result; different body→409.
- [ ] Idempotency: concurrent pay → INSERT ON CONFLICT winner proceeds, loser gets cached.
- [ ] Logistics event append uses FOR UPDATE; concurrent different-key appends both persist.
- [ ] Audit logs created for pay/ship/deliver/cancel/product change.
- [ ] Audit changes contain no password/token/full phone/full address.
- [ ] Seed script idempotent on re-run.
- [ ] GitHub Actions CI passes.

---

## Known Limitations

- **No server-side Refresh Token revocation.** Short Access Token TTL (30 min) mitigates.
- **No payment_gateway table.** Payment is simulated by status transition.
- **No shopping cart.** Direct order creation only.
- **No inventory reservation.** Stock checked at create, deducted at pay.
- **No PAID order cancellation.** All paid+ order cancellations deferred to Phase 02B after-sales flow.

---

## Deferred to Phase 02B

- after_sales_tickets, refund_records, reshipment_orders tables.
- order_items.is_refunded column.
- order_status.REFUNDING, REFUNDED (via enum migration: create-new-type → convert → drop-old → rename).
- PAID → CANCELLED with stock restoration and refund logic.
- Refund calculation, after-sales eligibility rules.
- Ticket/Refund/Reshipment APIs.
- 13 additional PostgreSQL enums.

---

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
- **Reviewer:** Self
