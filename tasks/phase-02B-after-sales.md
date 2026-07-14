# Phase 02B — After-sales Business Backend

## Phase Goals

Implement deterministic after-sales business logic: tickets, refunds, reshipments. Add `REFUNDED` to order_status via enum migration. Add `refunded_quantity`/`reshipped_quantity` tracking to order_items. Implement eligibility rules, cumulative refund cap, stock restoration, and row-level lock ordering. All operations are deterministic code — no LLM, no Agent.

## Revision History

- **2026-07-13 (v1):** Initial plan from Phase 02 split.
- **2026-07-13 (v2):** Added enum migration strategy, PAID cancel moved from 02A.
- **2026-07-13 (v3):** Full detailed design after Phase 02A audit.
- **2026-07-14 (v4):** 12 design corrections — partial refund Plan B, atomic refund, JSONB item details, unified idempotency, cancel boundary, PROCESSING→NEEDS_REVIEW, agent_notes→operator_notes, PostgreSQL sequences, config scope, migration rollback.
- **2026-07-14 (v5):** 9-point final fix:
  - **(1) Cumulative refund cap:** SUM(existing refund_records.refund_amount) + current ≤ order.paid_amount. Add `shipping_refund_amount` with cumulative cap ≤ order.shipping_fee.
  - **(2) Lock ordering:** Explicit lock order for refund (ticket→order→order_items→products) and reshipment (ticket→order_items→products). Re-validate after locking.
  - **(3) Cross-key duplicate guard:** UNIQUE(ticket_id) on refund_records and reshipment_orders. One execution resource per ticket. Refund/reshipment mutual exclusion via ticket lock + cross-table check.
  - **(4) Reshipment logistics:** Add tracking_number, carrier, shipped_at, delivered_at. SHIPPED cannot be cancelled.
  - **(5) Remove PROCESSING:** ticket_status reduced to 5 states (APPROVED, REJECTED, COMPLETED, CANCELLED, NEEDS_REVIEW). APPROVED→COMPLETED on success, APPROVED→NEEDS_REVIEW on foreseeable business failure. Transaction orchestration in Service layer, not Router.
  - **(6) Remove refund_status:** Delete refund_status enum. Remove status column from refund_records. Row existence = success.
  - **(7) Active ticket dedup:** Partial unique index on (order_id, intent, request_fingerprint) WHERE status IN ('APPROVED','NEEDS_REVIEW'). request_fingerprint = SHA256(canonical requested_items).
  - **(8) API count:** 13 endpoints (4 customer + 9 operator/admin).
  - **(9) Downgrade protection:** 6 assertion checks before downgrade; no silent data loss.

## Preconditions

- Phase 02A completed and CI green (8 tables, 5 enums, 18 API endpoints, 33 tests).
- Test database available (PostgreSQL + pgvector).
- order_items has NO refund tracking fields yet — added by migration 003.
- order_status has NO REFUNDED yet — added by migration 003.
- ProductRepository has `deduct_stock(pid, qty)`, `restore_stock(pid, qty)`, `get_by_ids_for_update(pids)`.
- IdempotencyRepository has `acquire_or_get`, `get_for_update`, `complete`.
- idempotency_records has `resource_id` column (UUID, nullable) — reused for Phase 02B resources.

---

## 1. Final Design Summary (v5)

### 1.1 Enums (5 new + 1 extended)

| Enum | Values | Notes |
|------|--------|-------|
| `intent_type` | LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, EXCHANGE, MISSING_PARTS, OTHER | 6 values |
| `ticket_status` | APPROVED, REJECTED, COMPLETED, CANCELLED, NEEDS_REVIEW | 5 values, NO PROCESSING |
| `resolution_type` | REFUND, EXCHANGE, RESHIPMENT, INFO_ONLY | 4 values |
| `refund_type` | FULL, PARTIAL, SHIPPING_FEE | 3 values |
| ~~`refund_status`~~ | **DELETED** | No status column on refund_records |
| `reshipment_status` | CREATED, SHIPPED, DELIVERED, CANCELLED | 4 values |
| `order_status` (extended) | +REFUNDED | 1 value added to existing enum |

**Total: 5 new enums + 1 order_status extension. No refund_status enum.**

`refund_status` is REMOVED because refund_records rows only exist when a refund succeeded. A single-value enum (SUCCEEDED) carries no business value. The presence of a row IS the success indicator. `created_at` provides timing. Future phases can reintroduce a status column with a VARCHAR CHECK or new enum if multi-step refund approval is needed.

### 1.2 Final Tables (3)

**after_sales_tickets:**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | gen_random_uuid() |
| ticket_number | VARCHAR(30) UNIQUE NOT NULL | TKT-{nextval} |
| user_id | UUID FK→users NOT NULL | |
| order_id | UUID FK→orders NOT NULL | |
| intent | intent_type NOT NULL | |
| status | ticket_status NOT NULL | APPROVED/REJECTED/COMPLETED/CANCELLED/NEEDS_REVIEW |
| resolution_type | resolution_type | nullable, set on completion |
| customer_request | TEXT | Original customer message |
| requested_items | JSONB NOT NULL | §1.3 schema, strict validation |
| request_fingerprint | VARCHAR(64) NOT NULL | SHA256(canonical requested_items) |
| operator_notes | TEXT | nullable, operator-written |
| proposed_solution | JSONB | nullable |
| resolution_result | JSONB | nullable, populated on completion |
| reject_reason | TEXT | nullable |
| reject_code | VARCHAR(20) | nullable |
| version | INTEGER DEFAULT 1 | Optimistic locking |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |
| completed_at | TIMESTAMPTZ | nullable |

Indexes:
- `ix_tickets_user_id` on (user_id)
- `ix_tickets_order_id` on (order_id)
- `ix_tickets_status` on (status)
- `ix_tickets_number` UNIQUE on (ticket_number)
- `uq_active_ticket_fingerprint` **PARTIAL UNIQUE** on (order_id, intent, request_fingerprint) WHERE status IN ('APPROVED', 'NEEDS_REVIEW')

No idempotency_key column. No agent_notes (renamed to operator_notes).

**refund_records:**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | gen_random_uuid() |
| ticket_id | UUID FK→after_sales_tickets UNIQUE NOT NULL | One refund per ticket |
| order_id | UUID FK→orders NOT NULL | |
| user_id | UUID FK→users NOT NULL | |
| refund_amount | NUMERIC(12,2) CHECK>0 NOT NULL | Server-computed total |
| shipping_refund_amount | NUMERIC(12,2) NOT NULL DEFAULT 0 | Shipping portion refunded |
| refund_type | refund_type NOT NULL | FULL/PARTIAL/SHIPPING_FEE |
| refund_reason | TEXT | |
| refund_items | JSONB NOT NULL | §1.4 immutable snapshot |
| calculation_breakdown | JSONB | Itemized calculation detail |
| rule_version | VARCHAR(20) | "02B-v1" |
| version | INTEGER DEFAULT 1 | |
| processed_by | UUID FK→users | Operator/admin who executed |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

Indexes:
- `ix_refunds_ticket_id` UNIQUE on (ticket_id) — prevents duplicate refund per ticket
- `ix_refunds_order_id` on (order_id)

No status column (row existence = success). No idempotency_key column.

**reshipment_orders:**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | gen_random_uuid() |
| ticket_id | UUID FK→after_sales_tickets UNIQUE NOT NULL | One reshipment per ticket |
| original_order_id | UUID FK→orders NOT NULL | |
| user_id | UUID FK→users NOT NULL | |
| reshipment_number | VARCHAR(30) UNIQUE NOT NULL | RSH-{nextval} |
| missing_items | JSONB NOT NULL | §1.4 schema |
| shipping_address | TEXT NOT NULL | Copied from original order |
| status | reshipment_status NOT NULL | CREATED/SHIPPED/DELIVERED/CANCELLED |
| tracking_number | VARCHAR(50) UNIQUE NULL | Set on SHIPPED |
| carrier | VARCHAR(50) NULL | Set on SHIPPED |
| shipped_at | TIMESTAMPTZ NULL | Set on SHIPPED |
| delivered_at | TIMESTAMPTZ NULL | Set on DELIVERED |
| version | INTEGER DEFAULT 1 | |
| processed_by | UUID FK→users | Operator/admin who created |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

Indexes:
- `ix_reshipments_ticket_id` UNIQUE on (ticket_id) — prevents duplicate reshipment per ticket
- `ix_reshipments_order_id` on (original_order_id)
- `ix_reshipments_number` UNIQUE on (reshipment_number)
- `ix_reshipments_tracking` UNIQUE on (tracking_number) — nullable columns allowed in unique index

No idempotency_key column.

### 1.3 JSONB Schemas

**requested_items (after_sales_tickets):**

```json
[
  {
    "order_item_id": "550e8400-e29b-41d4-a716-446655440000",
    "product_id": "660e8400-e29b-41d4-a716-446655440001",
    "quantity": 1,
    "reason_code": "DAMAGED"
  }
]
```

Validation rules (Service layer, before INSERT):
- `order_item_id` must exist in order_items and belong to the given order.
- `product_id` must match `order_item.product_id`.
- `quantity` must be a positive integer, ≤ `order_item.quantity - order_item.refunded_quantity - order_item.reshipped_quantity`.
- `reason_code` must be a non-empty string.
- Client-provided product names or prices are REJECTED.

**refund_items (refund_records) — immutable snapshot:**

```json
[
  {
    "order_item_id": "550e8400-e29b-41d4-a716-446655440000",
    "product_id": "660e8400-e29b-41d4-a716-446655440001",
    "quantity": 1,
    "unit_price": "199.99",
    "item_refund_amount": "199.99"
  }
]
```

Each element computed server-side from `order_item.unit_price × quantity`. Prices in this JSONB are historical snapshots — future logic MUST read from DB, never from this JSONB.

**missing_items (reshipment_orders):**

```json
[
  {
    "order_item_id": "550e8400-e29b-41d4-a716-446655440000",
    "product_id": "660e8400-e29b-41d4-a716-446655440001",
    "quantity": 1,
    "product_name_snapshot": "Wireless Earbuds"
  }
]
```

`product_name_snapshot` is informational only. Stock deduction reads `product.stock` and `product.id` from DB.

**request_fingerprint (after_sales_tickets):**

```python
def compute_request_fingerprint(requested_items: list[dict]) -> str:
    """SHA-256 of canonical requested_items for dedup."""
    canonical = json.dumps(
        sorted([
            {
                "order_item_id": item["order_item_id"],
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "reason_code": item.get("reason_code", ""),
            }
            for item in requested_items
        ], key=lambda x: x["order_item_id"]),
        sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
```

Computed server-side. Client does NOT submit request_fingerprint.

---

## 2. Cumulative Refund Cap

### 2.1 Formula

```
SUM(refund_records.refund_amount WHERE order_id = ?) + current_refund_amount
    <= order.paid_amount
```

```
SUM(refund_records.shipping_refund_amount WHERE order_id = ?) + current_shipping_refund
    <= order.shipping_fee
```

### 2.2 Implementation

In the refund transaction, after locking `order FOR UPDATE`:

```python
# Query existing refunds for this order (within the locked transaction)
existing_refunds = await refund_repo.list_by_order(order_id)
cumulative_refund = sum(r.refund_amount for r in existing_refunds)
cumulative_shipping = sum(r.shipping_refund_amount for r in existing_refunds)

remaining_refundable = order.paid_amount - cumulative_refund
remaining_shipping = order.shipping_fee - cumulative_shipping

if current_refund_amount > remaining_refundable:
    raise ValidationError(
        f"Cumulative refund ({cumulative_refund} + {current_refund_amount}) "
        f"exceeds paid amount ({order.paid_amount})"
    )

if current_shipping_refund > remaining_shipping:
    raise ValidationError(
        f"Cumulative shipping refund ({cumulative_shipping} + {current_shipping_refund}) "
        f"exceeds shipping fee ({order.shipping_fee})"
    )
```

RefundCalculator computes `total_refund_amount` and `shipping_refund_amount`. Both are validated against cumulative caps AFTER locks are held.

### 2.3 Shipping Fee Refund Rules

- Full refund (all order_items fully refunded): shipping fee may be refunded.
- Shipping-specific complaint: shipping fee may be refunded.
- Partial refund (not all items): shipping fee NOT refunded.
- Shipping fee can only be refunded once (cumulative cap).

The `calculation_breakdown` JSONB documents whether shipping was included and why.

---

## 3. Lock Ordering

### 3.1 Refund Lock Order

```
1. after_sales_ticket FOR UPDATE       (validate status=APPROVED, version)
2. orders FOR UPDATE                   (validate not REFUNDED, read paid_amount/shipping_fee)
3. order_items FOR UPDATE              (sorted by id ASC, validate refundable qty)
4. products FOR UPDATE                 (sorted by product_id ASC, only if stock restoration needed)
```

After acquiring ALL locks, re-validate:
- Ticket status is APPROVED, version matches
- Order status is not REFUNDED
- No existing refund_record with this ticket_id
- No existing reshipment_order with this ticket_id
- Each requested quantity ≤ order_item.quantity - order_item.refunded_quantity
- Cumulative refund amounts within caps (§2)

### 3.2 Reshipment Lock Order

```
1. after_sales_ticket FOR UPDATE       (validate status=APPROVED, version)
2. order_items FOR UPDATE              (sorted by id ASC, validate reshippable qty)
3. products FOR UPDATE                 (sorted by product_id ASC)
```

After acquiring ALL locks, re-validate:
- Ticket status is APPROVED, version matches
- No existing reshipment_order with this ticket_id
- No existing refund_record with this ticket_id (mutual exclusion)
- Each requested quantity ≤ order_item.quantity - order_item.reshipped_quantity
- Product stock ≥ requested quantity for each item

### 3.3 Reshipment Cancel Lock Order

```
1. reshipment_order FOR UPDATE         (validate status=CREATED, version)
2. products FOR UPDATE                 (sorted by product_id ASC, for stock restoration)
```

### 3.4 Ship/Deliver Reshipment Lock Order

```
1. reshipment_order FOR UPDATE         (validate transition, version)
```

---

## 4. Cross-Key Duplicate Execution Prevention

### 4.1 Database Constraints

```sql
-- refund_records: one refund per ticket
ALTER TABLE refund_records ADD CONSTRAINT uq_refunds_ticket UNIQUE (ticket_id);

-- reshipment_orders: one reshipment per ticket
ALTER TABLE reshipment_orders ADD CONSTRAINT uq_reshipments_ticket UNIQUE (ticket_id);
```

### 4.2 Cross-Table Mutual Exclusion

Refund and reshipment are mutually exclusive for a single ticket. Enforced by:

1. In refund tx: lock ticket FOR UPDATE → check no reshipment_order WHERE ticket_id = ?
2. In reshipment tx: lock ticket FOR UPDATE → check no refund_record WHERE ticket_id = ?
3. Both refund_records.ticket_id and reshipment_orders.ticket_id have UNIQUE constraints.

Concurrent refund + reshipment on the same ticket:
- Tx A (refund): locks ticket → checks both tables (empty) → inserts refund → commits
- Tx B (reshipment): waits for ticket lock → checks both tables → finds refund_record → raises 409

### 4.3 Different Idempotency Keys, Same Ticket

Two operators use different idempotency keys to execute a refund on the same ticket:

```
Tx A: acquire idempotency (key-A, refund_execute) → lock ticket → validate → insert refund → complete idempotency → commit
Tx B: acquire idempotency (key-B, refund_execute) → lock ticket → wait for Tx A...
      → ticket version mismatch OR UNIQUE(ticket_id) violation → rollback
```

The UNIQUE(ticket_id) constraint is the final defense. The version check and post-lock validation provide early detection. The idempotency key for Tx B is consumed (rolls back with the tx), so the operator can retry with a fresh key — but will get 409 since the refund already exists.

---

## 5. Active Ticket Concurrent Dedup

### 5.1 Partial Unique Index

```sql
ALTER TABLE after_sales_tickets ADD COLUMN request_fingerprint VARCHAR(64) NOT NULL;

CREATE UNIQUE INDEX uq_active_ticket_fingerprint
ON after_sales_tickets (order_id, intent, request_fingerprint)
WHERE status IN ('APPROVED', 'NEEDS_REVIEW');
```

### 5.2 Rationale for request_fingerprint

Without fingerprint: one active ticket per order+intent. A customer with two different items needing refund (same QUALITY_REFUND intent) would be forced to bundle them into one ticket.

With fingerprint: different requested_items produce different fingerprints, allowing separate tickets for distinct item-level issues. Exact-duplicate tickets (same items, same reason) are blocked.

The fingerprint is computed server-side from validated `requested_items`. The client cannot forge it.

### 5.3 Concurrent Creation Protection

Two concurrent POST /tickets with identical (order_id, intent, requested_items):
- Tx A: validates eligibility → INSERT ticket → partial unique index accepts → commits
- Tx B: validates eligibility → INSERT ticket → partial unique index VIOLATION → rolls back

The partial unique index is the database-level guard. Application-level duplicate check (SELECT existing tickets) is a fast-path hint, not the enforcement mechanism.

---

## 6. State Machines

### 6.1 Order Status

```
PENDING_PAYMENT ──pay──► PAID ──ship──► SHIPPED ──deliver──► DELIVERED
       │                             │              │              │
       └──cancel──► CANCELLED        │              │              │
                                     │              │              │
                                     └──full_refund─┼──full_refund─┘
                                                     │
                                                     ▼
                                                 REFUNDED
```

New transitions:
- PAID → REFUNDED (when ALL order_items.refunded_quantity == order_items.quantity)
- SHIPPED → REFUNDED (same condition)
- DELIVERED → REFUNDED (same condition)

Partial refund: order status UNCHANGED (stays PAID/SHIPPED/DELIVERED). Transition to REFUNDED only on the refund that makes the order fully refunded.

No REFUNDING. No PARTIALLY_REFUNDED.

### 6.2 Ticket Status (5 states)

```
                       ┌──► APPROVED ──success──► COMPLETED
(create+validate) ─────┤                    │
                       │                    └──foreseeable_failure──► NEEDS_REVIEW
                       ├──► REJECTED                                  │
                       │                                              │
                       └──► NEEDS_REVIEW ──approve──► APPROVED ──────┘
                               │    │
                               │    └──reject──► REJECTED
                               │
                               └──cancel──► CANCELLED

APPROVED ──cancel──► CANCELLED
```

| From | To | Actor | Notes |
|------|----|-------|-------|
| — | APPROVED | System | Eligible after creation |
| — | REJECTED | System | Not eligible after creation |
| — | NEEDS_REVIEW | System | Risk triggers after creation |
| APPROVED | CANCELLED | CUSTOMER | Customer cancels before operator acts |
| NEEDS_REVIEW | CANCELLED | CUSTOMER | Customer cancels before operator acts |
| NEEDS_REVIEW | APPROVED | OPERATOR/ADMIN | Operator approves |
| NEEDS_REVIEW | REJECTED | OPERATOR/ADMIN | Operator rejects |
| APPROVED | COMPLETED | System | Refund or reshipment succeeded atomically |
| APPROVED | NEEDS_REVIEW | System | Foreseeable business failure (e.g., insufficient stock), committed |

Terminal states: REJECTED, COMPLETED, CANCELLED.

No PROCESSING state. Refund and reshipment execute in a single transaction — the ticket goes directly from APPROVED to COMPLETED (success) or APPROVED to NEEDS_REVIEW (foreseeable failure). Unexpected exceptions roll back the entire transaction; the ticket remains APPROVED.

### 6.3 Reshipment Status

```
CREATED ──ship──► SHIPPED ──deliver──► DELIVERED
    │
    └──cancel──► CANCELLED
```

| From | To | Actor | Notes |
|------|----|-------|-------|
| — | CREATED | OPERATOR/ADMIN | Reshipment created, stock deducted atomically |
| CREATED | SHIPPED | OPERATOR/ADMIN | Sets tracking_number, carrier, shipped_at (required) |
| SHIPPED | DELIVERED | OPERATOR/ADMIN | Sets delivered_at |
| CREATED | CANCELLED | OPERATOR/ADMIN | Restores stock. SHIPPED cannot be cancelled. |

Version check on all transitions.

---

## 7. Transaction Design

All transactions committed by `get_db`. Service layer owns transaction orchestration. Router/API layer must NOT catch exceptions and open new DB transactions for ticket state changes.

### 7.1 Create Ticket

```
BEGIN
  1. Idempotency: acquire_or_get (ticket_create, user_id, key)
  2. Load order + order_items (non-locking read)
  3. Validate requested_items JSONB structure
  4. Validate each order_item_id belongs to order, product_id matches
  5. Compute request_fingerprint from canonical requested_items
  6. Run eligibility checks → determine initial status
  7. INSERT after_sales_tickets (partial unique index prevents duplicate active ticket)
  8. INSERT audit_log
  9. Idempotency: complete (resource_id = ticket.id)
COMMIT
```

### 7.2 Approve / Reject Ticket

```
BEGIN
  1. Idempotency: acquire_or_get (ticket_approve|ticket_reject, op_id, key)
  2. Load ticket FOR UPDATE, version-check
  3. Validate transition: NEEDS_REVIEW → APPROVED|REJECTED
  4. UPDATE ticket SET status, version+1
  5. INSERT audit_log
  6. Idempotency: complete
COMMIT
```

### 7.3 Execute Refund (Service layer, single transaction)

```
BEGIN
  1. Idempotency: acquire_or_get (refund_execute, op_id, key)
  2. Lock ticket FOR UPDATE → validate status=APPROVED, version
  3. Lock order FOR UPDATE → validate not REFUNDED
  4. Lock order_items FOR UPDATE (sorted by id ASC)
  5. Lock products FOR UPDATE (sorted by product_id ASC, if stock restoration)
  6. RE-VALIDATE after locks held:
     a. No existing refund_record with this ticket_id
     b. No existing reshipment_order with this ticket_id
     c. Each refund quantity ≤ order_item.quantity - order_item.refunded_quantity
  7. Query existing refunds for this order → compute cumulative_refund, cumulative_shipping
  8. Calculate refund amount → validate total ≤ order.paid_amount - cumulative_refund
  9. Calculate shipping refund → validate ≤ order.shipping_fee - cumulative_shipping
  10. If stock restoration needed: UPDATE products.stock += qty (PAID/SHIPPED only)
  11. UPDATE order_items.refunded_quantity += qty
  12. If full refund (all items refunded_quantity == quantity): UPDATE order SET status=REFUNDED
  13. INSERT refund_records (refund_items=snapshot, shipping_refund_amount)
  14. UPDATE ticket SET status=COMPLETED, resolution_type=REFUND
  15. INSERT audit_log (ticket + refund + order)
  16. Idempotency: complete (resource_id = refund.id)
COMMIT
```

**On unexpected exception:** entire tx rolls back. Ticket stays APPROVED. Idempotency key freed for retry.

### 7.4 Create Reshipment (Service layer, single transaction)

```
BEGIN
  1. Idempotency: acquire_or_get (reshipment_create, op_id, key)
  2. Lock ticket FOR UPDATE → validate status=APPROVED, version
  3. Lock order_items FOR UPDATE (sorted by id ASC)
  4. Lock products FOR UPDATE (sorted by product_id ASC)
  5. RE-VALIDATE after locks held:
     a. No existing reshipment_order with this ticket_id
     b. No existing refund_record with this ticket_id
     c. Each reship qty ≤ order_item.quantity - order_item.reshipped_quantity
     d. Product stock ≥ requested qty for each item
  6. IF stock insufficient (foreseeable failure):
     a. UPDATE ticket SET status=NEEDS_REVIEW, operator_notes="Insufficient stock: {details}"
     b. INSERT audit_log
     c. Idempotency: complete (resource_id = ticket.id, note: no reshipment created)
     d. COMMIT → returns {ticket_status: "NEEDS_REVIEW"}
  7. IF stock sufficient (success):
     a. UPDATE products.stock -= qty
     b. INSERT reshipment_orders (status=CREATED)
     c. UPDATE order_items.reshipped_quantity += qty
     d. UPDATE ticket SET status=COMPLETED, resolution_type=RESHIPMENT
     e. INSERT audit_log
     f. Idempotency: complete (resource_id = reshipment.id)
     g. COMMIT → returns {reshipment: {...}, ticket_status: "COMPLETED"}
```

### 7.5 Reshipment Lifecycle

```
POST /admin/reshipments/{id}/ship:
  BEGIN
    1. Idempotency: acquire_or_get (reshipment_ship, op_id, key)
    2. Lock reshipment FOR UPDATE → validate CREATED→SHIPPED, version
    3. UPDATE reshipment SET status=SHIPPED, tracking_number, carrier, shipped_at
    4. INSERT audit_log
    5. Idempotency: complete
  COMMIT

POST /admin/reshipments/{id}/deliver:
  BEGIN
    1. Idempotency: acquire_or_get (reshipment_deliver, op_id, key)
    2. Lock reshipment FOR UPDATE → validate SHIPPED→DELIVERED, version
    3. UPDATE reshipment SET status=DELIVERED, delivered_at
    4. INSERT audit_log
    5. Idempotency: complete
  COMMIT

POST /admin/reshipments/{id}/cancel:
  BEGIN
    1. Idempotency: acquire_or_get (reshipment_cancel, op_id, key)
    2. Lock reshipment FOR UPDATE → validate CREATED→CANCELLED, version
    3. Lock products FOR UPDATE (sorted by product_id ASC)
    4. UPDATE products.stock += qty (restore)
    5. UPDATE reshipment SET status=CANCELLED
    6. INSERT audit_log
    7. Idempotency: complete
  COMMIT
```

SHIPPED reshipments cannot be cancelled — returns 409.

---

## 8. API Design (13 Endpoints)

### 8.1 Customer Endpoints (4)

| # | Method | Path | Auth | Idempotency | Notes |
|---|--------|------|------|-------------|-------|
| 1 | POST | `/api/v1/after-sales/tickets` | CUSTOMER | Required | Body: {order_id, intent, requested_items, customer_request} |
| 2 | GET | `/api/v1/after-sales/tickets` | CUSTOMER | — | List own tickets, paginated |
| 3 | GET | `/api/v1/after-sales/tickets/{id}` | CUSTOMER | — | Ticket detail (own only) |
| 4 | POST | `/api/v1/after-sales/tickets/{id}/cancel` | CUSTOMER | Required | Cancel APPROVED or NEEDS_REVIEW ticket |

### 8.2 Operator/Admin Endpoints (9)

| # | Method | Path | Auth | Idempotency | Notes |
|---|--------|------|------|-------------|-------|
| 5 | GET | `/api/v1/admin/after-sales/tickets` | OPERATOR, ADMIN | — | List all tickets, filterable |
| 6 | GET | `/api/v1/admin/after-sales/tickets/{id}` | OPERATOR, ADMIN | — | Ticket detail |
| 7 | POST | `/api/v1/admin/after-sales/tickets/{id}/approve` | OPERATOR, ADMIN | Required | NEEDS_REVIEW → APPROVED |
| 8 | POST | `/api/v1/admin/after-sales/tickets/{id}/reject` | OPERATOR, ADMIN | Required | NEEDS_REVIEW → REJECTED |
| 9 | POST | `/api/v1/admin/after-sales/tickets/{id}/refund` | OPERATOR, ADMIN | Required | APPROVED → refund execute |
| 10 | POST | `/api/v1/admin/after-sales/tickets/{id}/reship` | OPERATOR, ADMIN | Required | APPROVED → reshipment create |
| 11 | POST | `/api/v1/admin/reshipments/{id}/ship` | OPERATOR, ADMIN | Required | CREATED → SHIPPED |
| 12 | POST | `/api/v1/admin/reshipments/{id}/deliver` | OPERATOR, ADMIN | Required | SHIPPED → DELIVERED |
| 13 | POST | `/api/v1/admin/reshipments/{id}/cancel` | OPERATOR, ADMIN | Required | CREATED → CANCELLED |

### 8.3 Cancel Endpoint (Unchanged)

`POST /api/v1/orders/{id}/cancel` — PENDING_PAYMENT only. No extension. Returns 409 for PAID/SHIPPED/DELIVERED. All after-sales flow goes through endpoint #1.

---

## 9. RBAC Matrix

| Operation | CUSTOMER | OPERATOR | ADMIN |
|-----------|----------|----------|-------|
| Create ticket (own order) | ✅ | — | — |
| View own tickets | ✅ | ✅ | ✅ |
| Cancel own APPROVED/NEEDS_REVIEW ticket | ✅ | — | — |
| View all tickets | ❌ | ✅ | ✅ |
| Approve/Reject tickets | ❌ | ✅ | ✅ |
| Execute refund | ❌ | ✅ | ✅ |
| Create/manage reshipments | ❌ | ✅ | ✅ |

No config write API in Phase 02B.

---

## 10. Idempotency Operations

| Operation | UNIQUE(user_id, operation, idempotency_key) | resource_id → |
|-----------|---------------------------------------------|--------------|
| `ticket_create` | user_id + `ticket_create` + key | after_sales_tickets.id |
| `ticket_cancel` | user_id + `ticket_cancel` + key | after_sales_tickets.id |
| `ticket_approve` | op_id + `ticket_approve` + key | after_sales_tickets.id |
| `ticket_reject` | op_id + `ticket_reject` + key | after_sales_tickets.id |
| `refund_execute` | op_id + `refund_execute` + key | refund_records.id or ticket.id |
| `reshipment_create` | op_id + `reshipment_create` + key | reshipment_orders.id or ticket.id |
| `reshipment_ship` | op_id + `reshipment_ship` + key | reshipment_orders.id |
| `reshipment_deliver` | op_id + `reshipment_deliver` + key | reshipment_orders.id |
| `reshipment_cancel` | op_id + `reshipment_cancel` + key | reshipment_orders.id |

Same INSERT ON CONFLICT DO NOTHING RETURNING pattern as Phase 02A.

---

## 11. Migration (003_create_after_sales_tables.py)

### 11.1 Upgrade

```sql
-- 1. New sequences
CREATE SEQUENCE ticket_number_seq START 100001;
CREATE SEQUENCE reshipment_number_seq START 100001;

-- 2. Extend order_status enum
CREATE TYPE order_status_new AS ENUM (
  'PENDING_PAYMENT','PAID','SHIPPED','DELIVERED','CANCELLED','REFUNDED'
);
ALTER TABLE orders ALTER COLUMN status TYPE order_status_new
  USING status::text::order_status_new;
DROP TYPE order_status;
ALTER TYPE order_status_new RENAME TO order_status;

-- 3. New enums (5)
CREATE TYPE intent_type AS ENUM (
  'LOGISTICS_INQUIRY','PRE_SHIP_REFUND','QUALITY_REFUND',
  'EXCHANGE','MISSING_PARTS','OTHER'
);
CREATE TYPE ticket_status AS ENUM (
  'APPROVED','REJECTED','COMPLETED','CANCELLED','NEEDS_REVIEW'
);
CREATE TYPE resolution_type AS ENUM (
  'REFUND','EXCHANGE','RESHIPMENT','INFO_ONLY'
);
CREATE TYPE refund_type AS ENUM ('FULL','PARTIAL','SHIPPING_FEE');
CREATE TYPE reshipment_status AS ENUM (
  'CREATED','SHIPPED','DELIVERED','CANCELLED'
);

-- 4. ALTER order_items
ALTER TABLE order_items ADD COLUMN refunded_quantity INTEGER NOT NULL DEFAULT 0;
ALTER TABLE order_items ADD COLUMN reshipped_quantity INTEGER NOT NULL DEFAULT 0;
ALTER TABLE order_items ADD CHECK (refunded_quantity >= 0);
ALTER TABLE order_items ADD CHECK (reshipped_quantity >= 0);
ALTER TABLE order_items ADD CHECK (refunded_quantity + reshipped_quantity <= quantity);

-- 5. Create after_sales_tickets
CREATE TABLE after_sales_tickets (...);
CREATE UNIQUE INDEX uq_active_ticket_fingerprint
  ON after_sales_tickets (order_id, intent, request_fingerprint)
  WHERE status IN ('APPROVED', 'NEEDS_REVIEW');

-- 6. Create refund_records
CREATE TABLE refund_records (...);
ALTER TABLE refund_records ADD CONSTRAINT uq_refunds_ticket UNIQUE (ticket_id);

-- 7. Create reshipment_orders
CREATE TABLE reshipment_orders (...);
ALTER TABLE reshipment_orders ADD CONSTRAINT uq_reshipments_ticket UNIQUE (ticket_id);
```

### 11.2 Downgrade (with 6 assertions)

```sql
-- ASSERTION 1: No after-sales data
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM after_sales_tickets) THEN
    RAISE EXCEPTION 'DOWNGRADE BLOCKED: after_sales_tickets is not empty. Delete all rows first.';
  END IF;
END $$;

-- ASSERTION 2: No refund data
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM refund_records) THEN
    RAISE EXCEPTION 'DOWNGRADE BLOCKED: refund_records is not empty. Delete all rows first.';
  END IF;
END $$;

-- ASSERTION 3: No reshipment data
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM reshipment_orders) THEN
    RAISE EXCEPTION 'DOWNGRADE BLOCKED: reshipment_orders is not empty. Delete all rows first.';
  END IF;
END $$;

-- ASSERTION 4: No REFUNDED orders
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM orders WHERE status = 'REFUNDED') THEN
    RAISE EXCEPTION 'DOWNGRADE BLOCKED: orders with REFUNDED status exist. Revert orders to previous status first.';
  END IF;
END $$;

-- ASSERTION 5: No refunded quantities
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM order_items WHERE refunded_quantity > 0) THEN
    RAISE EXCEPTION 'DOWNGRADE BLOCKED: order_items have non-zero refunded_quantity. Reset to 0 first.';
  END IF;
END $$;

-- ASSERTION 6: No reshipped quantities
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM order_items WHERE reshipped_quantity > 0) THEN
    RAISE EXCEPTION 'DOWNGRADE BLOCKED: order_items have non-zero reshipped_quantity. Reset to 0 first.';
  END IF;
END $$;

-- All assertions passed — proceed with DDL
DROP TABLE reshipment_orders;
DROP TABLE refund_records;
DROP TABLE after_sales_tickets;

DROP SEQUENCE reshipment_number_seq;
DROP SEQUENCE ticket_number_seq;

-- Revert order_status enum
CREATE TYPE order_status_old AS ENUM (
  'PENDING_PAYMENT','PAID','SHIPPED','DELIVERED','CANCELLED'
);
ALTER TABLE orders ALTER COLUMN status TYPE order_status_old
  USING status::text::order_status_old;
DROP TYPE order_status;
ALTER TYPE order_status_old RENAME TO order_status;

-- Drop new enums
DROP TYPE reshipment_status;
DROP TYPE refund_type;
DROP TYPE resolution_type;
DROP TYPE ticket_status;
DROP TYPE intent_type;

-- Drop order_items columns
ALTER TABLE order_items DROP COLUMN reshipped_quantity;
ALTER TABLE order_items DROP COLUMN refunded_quantity;
```

Every assertion failure produces a clear, descriptive error. No silent data loss.

---

## 12. File List

```
NEW FILES (~25):
backend/alembic/versions/003_create_after_sales_tables.py
backend/app/models/after_sales_ticket.py
backend/app/models/refund_record.py
backend/app/models/reshipment_order.py
backend/app/models/enums.py                         [UPDATE: +5 enums, +REFUNDED, -refund_status]
backend/app/repositories/ticket.py
backend/app/repositories/refund.py
backend/app/repositories/reshipment.py
backend/app/services/ticket.py
backend/app/services/refund.py
backend/app/services/reshipment.py
backend/app/rules/eligibility.py
backend/app/rules/refund_calculator.py
backend/app/rules/fingerprint.py                    [request_fingerprint computation]
backend/app/rules/state_transitions.py              [UPDATE: order + ticket + reshipment transitions]
backend/app/schemas/after_sales.py
backend/app/api/v1/after_sales.py                   [customer endpoints #1-4]
backend/app/api/v1/admin_after_sales.py             [operator endpoints #5-10]
backend/app/api/v1/admin_reshipments.py             [reshipment lifecycle #11-13]
backend/tests/integration/test_after_sales_api.py
backend/tests/integration/test_after_sales_rbac.py
backend/tests/integration/test_after_sales_idempotency.py
backend/tests/integration/test_after_sales_concurrency.py
backend/tests/unit/test_eligibility.py
backend/tests/unit/test_refund_calculator.py

MODIFIED FILES (~9):
backend/app/models/order_item.py                   [ADD: refunded_quantity, reshipped_quantity]
backend/app/models/__init__.py
backend/app/repositories/__init__.py
backend/app/services/__init__.py
backend/app/api/v1/__init__.py                     [ADD: after_sales routes]
backend/app/api/v1/orders.py                       [UNCHANGED: cancel stays PENDING_PAYMENT only]
backend/app/rules/state_transitions.py             [ADD: REFUNDED, ticket, reshipment transitions]
backend/app/schemas/order.py                       [ADD: refunded_quantity, reshipped_quantity to response]
backend/tests/conftest.py                          [ADD: after-sales fixtures]
```

---

## 13. Test Plan

### Unit Tests (7)
1. `test_eligibility.py` — All 7 reject codes trigger correctly
2. `test_eligibility.py` — NEEDS_REVIEW triggers (HIGH risk, >threshold, EXCHANGE, multi-item)
3. `test_refund_calculator.py` — Full refund calculation
4. `test_refund_calculator.py` — Partial refund, multi-item, Decimal precision
5. `test_refund_calculator.py` — Shipping fee refund logic (only refunded once)
6. `test_refund_calculator.py` — Cumulative cap enforcement (existing refunds + current > paid_amount)
7. State transition validation (ticket, refund, reshipment, order)

### Integration Tests (27)
8. Create ticket → auto-APPROVED → operator refund → verify order/stock
9. Create ticket → auto-REJECTED (verify reject_code)
10. Create ticket → NEEDS_REVIEW (HIGH risk user) → operator approve → refund
11. Customer cancels own APPROVED ticket
12. Customer cancels own NEEDS_REVIEW ticket
13. Refund PAID order → verify stock restored
14. Refund SHIPPED order → verify stock restored
15. Refund DELIVERED quality order → verify stock NOT restored
16. Partial refund → verify order status unchanged, refunded_quantity correct
17. Two partial refunds → verify cumulative tracking → second triggers full → order → REFUNDED
18. Cumulative refund exceeds paid_amount → 422
19. Shipping refund exceeds shipping_fee → 422
20. Shipping fee refunded only once (second attempt blocked)
21. Reshipment → verify stock deducted, reshipped_quantity updated
22. Reshipment → ship → deliver (verify timestamps and tracking_number)
23. Reshipment cancel (CREATED) → verify stock restored
24. Reshipment cancel (SHIPPED) → 409 (cannot cancel shipped)
25. Insufficient stock for reshipment → ticket → NEEDS_REVIEW, no reshipment created
26. request_fingerprint: same items → partial unique index blocks duplicate
27. request_fingerprint: different items → two tickets allowed
28. `test_after_sales_rbac.py` — Cross-user ticket access denied
29. `test_after_sales_rbac.py` — CUSTOMER cannot call operator endpoints
30. `test_after_sales_idempotency.py` — Double ticket create → replay
31. `test_after_sales_idempotency.py` — Double refund → replay
32. `test_after_sales_idempotency.py` — Same key different body → 409
33. `test_after_sales_concurrency.py` — Two different keys, same ticket refund → one wins, other 409
34. `test_after_sales_concurrency.py` — Concurrent refund + reshipment same ticket → one wins (mutual exclusion)

### Migration Tests (3)
35. Upgrade 002→003 creates 3 tables + 5 enums + 2 sequences + ALTERs + partial unique index
36. Downgrade 003→002: all 6 assertions pass on clean DB, drop succeeds
37. Downgrade blocked when REFUNDED order exists (assertion #4 error)

### Audit & Validation Tests (5)
38. Optimistic lock conflict on ticket (concurrent approve)
39. Audit sanitization (refund amounts logged, no PII)
40. requested_items validation: bad order_item_id, mismatched product_id, quantity=0
41. refund_items immutable snapshot correctness
42. request_fingerprint computed server-side, client value ignored

**Total: 42 tests** (7 unit + 27 integration + 3 migration + 5 audit/validation)

---

## 14. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Enum migration fails mid-way | Transactional DDL |
| REFUNDED orders on downgrade | Assertion check blocks with clear error |
| Concurrent refund on same ticket, different keys | UNIQUE(ticket_id) + ticket FOR UPDATE lock + post-lock validation |
| Concurrent refund + reshipment same ticket | Cross-table check after ticket lock + UNIQUE per table |
| Duplicate active tickets | Partial unique index on (order_id, intent, request_fingerprint) |
| Cumulative refund exceeds paid_amount | SUM existing refunds after order lock, validate before insert |
| Stock double-restore | No per-table idempotency_key; generic idempotency protects |
| Shipping fee refunded twice | shipping_refund_amount cumulative cap check after lock |
| Reshipment stock race | FOR UPDATE on products sorted; post-lock re-validation |
| Sequence gaps | Non-transactional sequences; gaps acceptable |
| Router modifies ticket in new tx | Transaction orchestration in Service layer only |

---

## 15. Deferred to Later Phases

| Content | Phase |
|---------|-------|
| approval_tasks table + human-in-the-loop | Phase 06 |
| Agent sessions, messages, tool logs, traces | Phase 03 |
| LangGraph state machine, Agent tools | Phase 03 |
| policy_documents table + RAG | Phase 04 |
| customer_memories table | Phase 05 |
| approval_type, approval_status enums | Phase 06 |
| session_status, message_role enums | Phase 03 |
| memory_type enum | Phase 05 |
| policy_category, policy_status enums | Phase 04 |
| Config write API (PUT /admin/config) | Phase 06 or later |
| EXCHANGE intent full implementation | Phase 06 |
| Multi-step refund with approval workflow | Phase 06 |
| refund_records status column (if needed) | Phase 06 |

---

## Acceptance Criteria

- [ ] `alembic upgrade head` creates 3 tables + 5 enums + 2 sequences + extends order_status + alters order_items
- [ ] Partial unique index on after_sales_tickets enforces active ticket dedup
- [ ] UNIQUE(ticket_id) on refund_records and reshipment_orders
- [ ] `alembic downgrade -1` with all 6 assertions passing → clean rollback
- [ ] `alembic downgrade -1` blocked with clear error when any assertion fails
- [ ] Ruff 0, Mypy 0
- [ ] All 42 tests pass on fresh database (self-contained, no seed dependency)
- [ ] Ticket creation: auto-validates → APPROVED/REJECTED/NEEDS_REVIEW
- [ ] Eligibility: all 7 reject codes trigger correctly
- [ ] Cumulative refund cap: SUM(existing) + current ≤ paid_amount
- [ ] Shipping refund cap: SUM(existing) + current ≤ shipping_fee; only refunded once
- [ ] Partial refund: order status unchanged; refunded_quantity tracked correctly
- [ ] Full refund (cumulative or single): order → REFUNDED
- [ ] Stock restored on PAID/SHIPPED refund; NOT restored on DELIVERED quality refund
- [ ] Reshipment: stock deducted atomically; insufficient → ticket NEEDS_REVIEW (committed)
- [ ] Reshipment lifecycle: ship (set tracking), deliver (set delivered_at), cancel (restore stock, CREATED only)
- [ ] Lock ordering enforced: ticket → order → order_items → products
- [ ] Post-lock re-validation: ticket status, version, quantities, cumulative amounts, stock
- [ ] Cross-key duplicate: UNIQUE(ticket_id) + cross-table mutual exclusion
- [ ] Idempotency: replay returns cached, different body → 409
- [ ] RBAC: cross-user, cross-role all blocked
- [ ] Audit: all mutating operations logged, no PII
- [ ] Transaction orchestration in Service layer; Router never opens new DB tx for ticket changes
- [ ] No idempotency_key columns on business tables
- [ ] No refund_status enum; no status column on refund_records
- [ ] No PROCESSING in ticket_status
- [ ] requested_items, refund_items, missing_items validated server-side
- [ ] request_fingerprint computed server-side
- [ ] ticket_number and reshipment_number use PostgreSQL sequences
- [ ] agent_notes renamed to operator_notes

---

## Completion Record

- **Started:** TBD
- **Completed:** TBD
- **Actual Effort:** TBD
