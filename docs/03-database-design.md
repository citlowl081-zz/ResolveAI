# 03 — Database Design

## Entity-Relationship Overview

```
users ──┬── orders ──┬── order_items ─── products
        │            │
        │            ├── logistics_records
        │            │
        │            └── after_sales_tickets ──┬── refund_records
        │                                      ├── reshipment_orders
        │                                      └── approval_tasks
        │
        ├── agent_sessions ─── agent_messages
        │
        ├── agent_tool_logs
        ├── agent_traces
        ├── customer_memories
        └── audit_logs

policy_documents (standalone, RAG)
system_configs (standalone)
evaluation_runs / evaluation_results (Phase 08 — not yet implemented, schema TBD)
```

## Tables

### 1. users
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen | Unique user ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| hashed_password | VARCHAR(255) | NOT NULL | Bcrypt hash |
| full_name | VARCHAR(100) | NOT NULL | Display name |
| phone | VARCHAR(20) | | Contact phone (masked in logs) |
| default_address | TEXT | | Default shipping address |
| role | user_role ENUM | NOT NULL | CUSTOMER, OPERATOR, ADMIN |
| risk_level | risk_level ENUM | DEFAULT 'LOW' | LOW, MEDIUM, HIGH |
| is_active | BOOLEAN | DEFAULT TRUE | Soft disable |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |

**Indexes:** `ix_users_email` UNIQUE on (email)

### 2. products
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| name | VARCHAR(200) | NOT NULL | Product name |
| description | TEXT | | Product description |
| category | product_category ENUM | NOT NULL | ELECTRONICS, CLOTHING, FOOD, HOME, SPORTS, OTHER |
| price | DECIMAL(10,2) | NOT NULL, CHECK > 0 | Unit price in CNY |
| stock | INTEGER | NOT NULL, DEFAULT 0 | Available stock |
| image_url | VARCHAR(500) | | Product image |
| is_returnable | BOOLEAN | DEFAULT TRUE | Whether returns are allowed |
| is_active | BOOLEAN | DEFAULT TRUE | Soft delete |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_products_category` on (category), `ix_products_active` on (is_active)

### 3. orders
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | |
| order_number | VARCHAR(30) | UNIQUE, NOT NULL | Human-readable order # |
| status | order_status ENUM | NOT NULL | PENDING_PAYMENT, PAID, SHIPPED, DELIVERED, CANCELLED, REFUNDED, PARTIALLY_REFUNDED |
| total_amount | DECIMAL(10,2) | NOT NULL | Order total |
| discount_amount | DECIMAL(10,2) | DEFAULT 0 | |
| paid_amount | DECIMAL(10,2) | DEFAULT 0 | Actual paid amount |
| shipping_address | TEXT | NOT NULL | |
| shipping_fee | DECIMAL(10,2) | DEFAULT 0 | |
| coupon_code | VARCHAR(50) | | Applied coupon |
| paid_at | TIMESTAMPTZ | | Payment timestamp |
| shipped_at | TIMESTAMPTZ | | Shipment timestamp |
| delivered_at | TIMESTAMPTZ | | Delivery timestamp |
| version | INTEGER | DEFAULT 1 | Optimistic locking |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_orders_user_id` on (user_id), `ix_orders_order_number` UNIQUE on (order_number), `ix_orders_status` on (status)

### 4. order_items
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| order_id | UUID | FK → orders.id, NOT NULL | |
| product_id | UUID | FK → products.id, NOT NULL | |
| product_name | VARCHAR(200) | NOT NULL | Snapshot at order time |
| unit_price | DECIMAL(10,2) | NOT NULL | Snapshot at order time |
| quantity | INTEGER | NOT NULL, CHECK > 0 | |
| subtotal | DECIMAL(10,2) | NOT NULL | unit_price * quantity |
| is_refunded | BOOLEAN | DEFAULT FALSE | Whether this item was refunded |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_order_items_order_id` on (order_id)

### 5. logistics_records
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| order_id | UUID | FK → orders.id, NOT NULL | |
| tracking_number | VARCHAR(50) | UNIQUE, NOT NULL | Mock tracking # |
| carrier | VARCHAR(50) | DEFAULT 'SF Express' | |
| status | logistics_status ENUM | NOT NULL | PENDING, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, RETURNED |
| current_location | VARCHAR(200) | | Last known location |
| estimated_delivery | TIMESTAMPTZ | | ETA |
| actual_delivery | TIMESTAMPTZ | | Actual delivery time |
| events | JSONB | DEFAULT '[]' | Timeline of logistics events |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_logistics_order_id` on (order_id), `ix_logistics_tracking` UNIQUE on (tracking_number)

### 6. after_sales_tickets
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_number | VARCHAR(30) | UNIQUE, NOT NULL | Human-readable ticket # |
| user_id | UUID | FK → users.id, NOT NULL | |
| order_id | UUID | FK → orders.id, NOT NULL | |
| intent | intent_type ENUM | NOT NULL | LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, EXCHANGE, MISSING_PARTS, ESCALATE_TO_HUMAN, OTHER |
| status | ticket_status ENUM | NOT NULL | OPEN, PROCESSING, PENDING_CONFIRMATION, PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED, CANCELLED |
| resolution_type | resolution_type ENUM | | REFUND, EXCHANGE, RESHIPMENT, INFO_ONLY, ESCALATED |
| customer_request | TEXT | | Original customer message |
| agent_notes | TEXT | | Agent's analysis |
| proposed_solution | JSONB | | Structured solution plan |
| resolution_result | JSONB | | Final outcome |
| idempotency_key | VARCHAR(100) | UNIQUE | Prevents duplicate creation |
| is_resumed | BOOLEAN | DEFAULT FALSE | Whether resumed from paused state |
| version | INTEGER | DEFAULT 1 | Optimistic locking |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| completed_at | TIMESTAMPTZ | | |

**Indexes:** `ix_tickets_user_id` on (user_id), `ix_tickets_order_id` on (order_id), `ix_tickets_status` on (status), `ix_tickets_idempotency` UNIQUE on (idempotency_key)

### 7. refund_records
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_id | UUID | FK → after_sales_tickets.id, NOT NULL | |
| order_id | UUID | FK → orders.id, NOT NULL | |
| user_id | UUID | FK → users.id, NOT NULL | |
| refund_amount | DECIMAL(10,2) | NOT NULL, CHECK > 0 | |
| refund_reason | TEXT | | |
| refund_type | refund_type ENUM | NOT NULL | FULL, PARTIAL, SHIPPING_FEE |
| status | refund_status ENUM | NOT NULL | PENDING, PROCESSING, APPROVED, COMPLETED, REJECTED |
| idempotency_key | VARCHAR(100) | UNIQUE | Prevents duplicate refunds |
| is_high_risk | BOOLEAN | DEFAULT FALSE | |
| approved_by | UUID | FK → users.id | Who approved |
| approved_at | TIMESTAMPTZ | | |
| version | INTEGER | DEFAULT 1 | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_refunds_ticket_id` on (ticket_id), `ix_refunds_order_id` on (order_id), `ix_refunds_idempotency` UNIQUE on (idempotency_key)

### 8. reshipment_orders
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_id | UUID | FK → after_sales_tickets.id, NOT NULL | |
| original_order_id | UUID | FK → orders.id, NOT NULL | |
| user_id | UUID | FK → users.id, NOT NULL | |
| reshipment_number | VARCHAR(30) | UNIQUE, NOT NULL | |
| missing_items | JSONB | NOT NULL | [{product_name, quantity}] |
| shipping_address | TEXT | NOT NULL | |
| status | reshipment_status ENUM | NOT NULL | PENDING, APPROVED, PROCESSING, SHIPPED, DELIVERED, CANCELLED |
| idempotency_key | VARCHAR(100) | UNIQUE | |
| version | INTEGER | DEFAULT 1 | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_reshipments_ticket_id` on (ticket_id), `ix_reshipments_idempotency` UNIQUE on (idempotency_key)

### 9. approval_tasks
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| ticket_id | UUID | FK → after_sales_tickets.id, NOT NULL | |
| task_type | approval_type ENUM | NOT NULL | REFUND, RESHIPMENT, HIGH_RISK |
| status | approval_status ENUM | NOT NULL | PENDING, APPROVED, REJECTED |
| requested_by | UUID | FK → users.id | Agent/system |
| assigned_to | UUID | FK → users.id | Approver |
| context | JSONB | | Full context for approval decision |
| decision_note | TEXT | | Approver's note |
| decided_at | TIMESTAMPTZ | | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_approvals_ticket_id` on (ticket_id), `ix_approvals_status` on (status), `ix_approvals_assigned_to` on (assigned_to)

### 10. agent_sessions
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| session_id | VARCHAR(50) | UNIQUE, NOT NULL | External session identifier |
| user_id | UUID | FK → users.id, NOT NULL | |
| thread_id | VARCHAR(50) | NOT NULL | Conversation thread |
| status | session_status ENUM | NOT NULL | ACTIVE, PAUSED, COMPLETED, EXPIRED |
| current_node | VARCHAR(50) | | Current LangGraph node |
| graph_state | JSONB | | Serialized LangGraph state |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| expires_at | TIMESTAMPTZ | | |

**Indexes:** `ix_sessions_session_id` UNIQUE on (session_id), `ix_sessions_user_id` on (user_id), `ix_sessions_thread_id` on (thread_id)

### 11. agent_messages
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| session_id | UUID | FK → agent_sessions.id, NOT NULL | |
| role | message_role ENUM | NOT NULL | USER, AGENT, SYSTEM, TOOL |
| content | TEXT | NOT NULL | |
| message_metadata | JSONB | | Structured metadata |
| token_count | INTEGER | | |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_messages_session_id` on (session_id)

### 12. agent_tool_logs
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| session_id | UUID | FK → agent_sessions.id, NOT NULL | |
| trace_id | VARCHAR(50) | NOT NULL | Links tool calls in a trace |
| tool_name | VARCHAR(100) | NOT NULL | |
| tool_input | JSONB | | Sanitized input |
| tool_output | JSONB | | Sanitized output |
| is_success | BOOLEAN | NOT NULL | |
| error_message | TEXT | | |
| duration_ms | INTEGER | | Execution time |
| retry_count | INTEGER | DEFAULT 0 | |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_tool_logs_session_id` on (session_id), `ix_tool_logs_trace_id` on (trace_id), `ix_tool_logs_tool_name` on (tool_name)

### 13. agent_traces
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| session_id | UUID | FK → agent_sessions.id, NOT NULL | |
| trace_id | VARCHAR(50) | NOT NULL | |
| node_name | VARCHAR(50) | NOT NULL | LangGraph node name |
| node_input | JSONB | | |
| node_output | JSONB | | |
| routing_decision | VARCHAR(50) | | Which edge was taken |
| duration_ms | INTEGER | | |
| error_info | JSONB | | Error details if failed |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_traces_session_id` on (session_id), `ix_traces_trace_id` on (trace_id)

### 14. customer_memories
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | |
| memory_type | memory_type ENUM | NOT NULL | SHORT_TERM, LONG_TERM, BUSINESS_STATE |
| key | VARCHAR(100) | NOT NULL | Memory key |
| value | JSONB | NOT NULL | Memory content |
| source | VARCHAR(50) | | Origin (session_id, event) |
| importance | INTEGER | DEFAULT 1 | 1-10 importance score |
| expires_at | TIMESTAMPTZ | | TTL for short-term memories |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_memories_user_type_key` UNIQUE on (user_id, memory_type, key), `ix_memories_user_id` on (user_id)

### 15. policy_documents
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| policy_id | VARCHAR(50) | UNIQUE, NOT NULL | Business identifier |
| title | VARCHAR(200) | NOT NULL | |
| category | policy_category ENUM | NOT NULL | RETURN, REFUND, EXCHANGE, RESHIPMENT, LOGISTICS, RISK, SOP |
| issue_type | VARCHAR(50) | | Matches intent types |
| content | TEXT | NOT NULL | Full policy text |
| content_summary | TEXT | | Brief summary |
| embedding | vector(1536) | | pgvector embedding |
| metadata_filter | JSONB | | Structured filter fields |
| effective_date | DATE | NOT NULL | |
| expiration_date | DATE | | |
| status | policy_status ENUM | NOT NULL | DRAFT, ACTIVE, SUPERSEDED, ARCHIVED |
| version | INTEGER | NOT NULL | |
| source | VARCHAR(100) | | Origin of policy |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_policies_policy_id` UNIQUE on (policy_id), `ix_policies_category` on (category), `ix_policies_status` on (status), `ix_policies_embedding` IVFFlat on (embedding)

### 16. audit_logs
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id | Who performed action |
| action | VARCHAR(50) | NOT NULL | CREATE, UPDATE, DELETE, APPROVE, REJECT, EXECUTE |
| resource_type | VARCHAR(50) | NOT NULL | ORDER, TICKET, REFUND, RESHIPMENT, POLICY, CONFIG |
| resource_id | UUID | | Affected resource |
| changes | JSONB | | Before/after snapshot |
| ip_address | VARCHAR(45) | | |
| user_agent | VARCHAR(500) | | |
| trace_id | VARCHAR(50) | | Links to agent trace |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_audit_user_id` on (user_id), `ix_audit_resource` on (resource_type, resource_id), `ix_audit_action` on (action), `ix_audit_created_at` on (created_at)

### 17. system_configs
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| config_key | VARCHAR(100) | UNIQUE, NOT NULL | |
| config_value | JSONB | NOT NULL | |
| description | TEXT | | |
| updated_by | UUID | FK → users.id | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `ix_configs_key` UNIQUE on (config_key)

## Enums

```sql
CREATE TYPE user_role AS ENUM ('CUSTOMER', 'OPERATOR', 'ADMIN');
CREATE TYPE risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH');
CREATE TYPE product_category AS ENUM ('ELECTRONICS', 'CLOTHING', 'FOOD', 'HOME', 'SPORTS', 'OTHER');
CREATE TYPE order_status AS ENUM ('PENDING_PAYMENT', 'PAID', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED', 'PARTIALLY_REFUNDED');
CREATE TYPE logistics_status AS ENUM ('PENDING', 'PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED', 'RETURNED');
CREATE TYPE intent_type AS ENUM ('LOGISTICS_INQUIRY', 'PRE_SHIP_REFUND', 'QUALITY_REFUND', 'EXCHANGE', 'MISSING_PARTS', 'ESCALATE_TO_HUMAN', 'OTHER');
CREATE TYPE ticket_status AS ENUM ('OPEN', 'PROCESSING', 'PENDING_CONFIRMATION', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'COMPLETED', 'CANCELLED');
CREATE TYPE resolution_type AS ENUM ('REFUND', 'EXCHANGE', 'RESHIPMENT', 'INFO_ONLY', 'ESCALATED');
CREATE TYPE refund_type AS ENUM ('FULL', 'PARTIAL', 'SHIPPING_FEE');
CREATE TYPE refund_status AS ENUM ('PENDING', 'PROCESSING', 'APPROVED', 'COMPLETED', 'REJECTED');
CREATE TYPE reshipment_status AS ENUM ('PENDING', 'APPROVED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED');
CREATE TYPE approval_type AS ENUM ('REFUND', 'RESHIPMENT', 'HIGH_RISK');
CREATE TYPE approval_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
CREATE TYPE session_status AS ENUM ('ACTIVE', 'PAUSED', 'COMPLETED', 'EXPIRED');
CREATE TYPE message_role AS ENUM ('USER', 'AGENT', 'SYSTEM', 'TOOL');
CREATE TYPE memory_type AS ENUM ('SHORT_TERM', 'LONG_TERM', 'BUSINESS_STATE');
CREATE TYPE policy_category AS ENUM ('RETURN', 'REFUND', 'EXCHANGE', 'RESHIPMENT', 'LOGISTICS', 'RISK', 'SOP');
CREATE TYPE policy_status AS ENUM ('DRAFT', 'ACTIVE', 'SUPERSEDED', 'ARCHIVED');
```

## Database Constraints & Rules

1. **Foreign Keys:** All relationships use FK constraints with appropriate ON DELETE (RESTRICT for most, CASCADE for session → messages).
2. **Unique Constraints:** order_number, ticket_number, tracking_number, idempotency_key fields.
3. **Check Constraints:** price > 0, quantity > 0, refund_amount > 0.
4. **Optimistic Locking:** orders, after_sales_tickets, refund_records, reshipment_orders use a `version` integer column.
5. **Soft Deletes:** users and products use `is_active` flag; policies use `status = ARCHIVED`.
6. **Timestamps:** All tables have `created_at`; mutable tables have `updated_at`.
7. **Audit Trail:** Every state-modifying operation on orders, tickets, refunds, reshipments, policies, and configs must create an audit_log row.

## Migration Strategy

- All schema changes via Alembic.
- Migration files in `backend/alembic/versions/`.
- `alembic upgrade head` runs on application startup in Docker.
- Test migrations with `alembic upgrade head && alembic downgrade -1`.
