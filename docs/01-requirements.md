# 01 — Requirements Document

## Functional Requirements

### FR-01: User Management
- FR-01.1: Users can register with email and password.
- FR-01.2: Users can log in and receive a JWT token.
- FR-01.3: Users have roles: CUSTOMER, OPERATOR, ADMIN.
- FR-01.4: JWT tokens expire after 30 minutes (access) and 7 days (refresh).

### FR-02: Product Catalog
- FR-02.1: Users can browse products with pagination.
- FR-02.2: Users can view product details (name, description, price, stock, images).
- FR-02.3: Products have categories (electronics, clothing, food, etc.).

### FR-03: Order Management
- FR-03.1: Users can place simulated orders.
- FR-03.2: Users can view their order list and order details.
- FR-03.3: Orders have statuses: PENDING_PAYMENT, PAID, SHIPPED, DELIVERED, CANCELLED, REFUNDED.
- FR-03.4: Order items track product, quantity, and unit price.

### FR-04: Logistics
- FR-04.1: Each order has logistics records with tracking numbers.
- FR-04.2: Logistics statuses: PENDING, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, RETURNED.
- FR-04.3: Users can query logistics by order ID or tracking number.

### FR-05: AI After-Sales Agent
- FR-05.1: Users can initiate after-sales conversations via WebSocket or HTTP.
- FR-05.2: Agent classifies intent into: LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, EXCHANGE, MISSING_PARTS, ESCALATE_TO_HUMAN.
- FR-05.3: Agent identifies the user and resolves which order they're referring to.
- FR-05.4: Agent retrieves applicable after-sales policies via RAG.
- FR-05.5: Agent checks eligibility using deterministic rules.
- FR-05.6: Agent calculates refund amounts using deterministic code (never the LLM).
- FR-05.7: Agent generates a resolution plan and asks for user confirmation.
- FR-05.8: Agent checks risk level and triggers human approval if needed.
- FR-05.9: Agent executes business tools (create ticket, create refund, create reshipment).
- FR-05.10: Agent verifies execution results by checking database state.
- FR-05.11: Agent handles interruptions and can resume across sessions.

### FR-06: After-Sales Tickets
- FR-06.1: System creates after-sales tickets for every after-sales request.
- FR-06.2: Ticket statuses: OPEN, PROCESSING, PENDING_APPROVAL, APPROVED, REJECTED, COMPLETED, CANCELLED.
- FR-06.3: Tickets are linked to orders and users.
- FR-06.4: Tickets track the resolution type (refund, exchange, reshipment).

### FR-07: Refunds
- FR-07.1: System creates refund records linked to tickets and orders.
- FR-07.2: Refund amounts are calculated deterministically based on order data and policy rules.
- FR-07.3: Refunds above a configurable threshold require human approval.
- FR-07.4: Duplicate refunds for the same order item are prevented via idempotency keys.

### FR-08: Reshipments
- FR-08.1: System creates reshipment orders for missing parts.
- FR-08.2: Reshipment orders are linked to original orders and tickets.
- FR-08.3: Duplicate reshipments are prevented via idempotency.

### FR-09: Human Approval
- FR-09.1: High-risk operations are paused and queued for human review.
- FR-09.2: OPERATOR and ADMIN roles can approve or reject pending tasks.
- FR-09.3: Approval decisions are logged in the audit trail.
- FR-09.4: Agent resumes from the saved state after approval/rejection.

### FR-10: RAG Knowledge Base
- FR-10.1: After-sales policies are stored as documents with embeddings.
- FR-10.2: Retrieval supports vector search with metadata filtering.
- FR-10.3: Policies have versions, effective dates, and active/inactive status.
- FR-10.4: When no relevant policy is found, agent escalates — never fabricates.

### FR-11: Memory System
- FR-11.1: Short-term memory (session): current intent, order, tool calls, confirmation state.
- FR-11.2: Long-term memory (user): preferences, history summaries, risk level.
- FR-11.3: Business state memory: active tickets, pending approvals, outstanding commitments.
- FR-11.4: Memory is isolated by user_id and thread_id.

### FR-12: Observability
- FR-12.1: Every tool call is logged with input, output, duration, and trace ID.
- FR-12.2: Agent execution path through the state machine is recorded.
- FR-12.3: All state-modifying operations create audit log entries.
- FR-12.4: Sensitive data (passwords, tokens, phone numbers, addresses) is masked in logs.

### FR-13: Admin Backend
- FR-13.1: Dashboard with key metrics (tickets, refunds, approvals).
- FR-13.2: Ticket management (view, filter, manage).
- FR-13.3: Approval center (pending, approved, rejected).
- FR-13.4: Policy management (CRUD, versioning).
- FR-13.5: Agent trace viewer.
- FR-13.6: Tool call log viewer.
- FR-13.7: Audit log viewer.
- FR-13.8: Evaluation results dashboard.
- FR-13.9: System configuration management.

### FR-14: Evaluation
- FR-14.1: 50+ evaluation cases covering all intent types and edge cases.
- FR-14.2: Metrics: intent accuracy, tool selection accuracy, parameter correctness, policy hit rate, task completion rate, safety interception rate, approval trigger accuracy.
- FR-14.3: Results are stored and viewable in the admin dashboard.

### FR-15: Security
- FR-15.1: JWT-based authentication on all endpoints.
- FR-15.2: Role-based access control enforced server-side.
- FR-15.3: Input validation on all endpoints (Pydantic/Zod).
- FR-15.4: Idempotency keys on all state-modifying operations.
- FR-15.5: Prompt injection detection on user messages.
- FR-15.6: Rate limiting on authentication and agent endpoints.
- FR-15.7: PII masking in all logs.

## Non-Functional Requirements

### NFR-01: Performance
- Agent response time < 30 seconds for standard flows.
- API response time < 200ms for CRUD operations.
- RAG retrieval < 500ms for top-5 results.

### NFR-02: Reliability
- Tool execution retries up to 2 times for transient failures.
- Agent session state is recoverable after interruption.
- Database transactions ensure consistency.

### NFR-03: Maintainability
- All code has type annotations.
- All public functions have docstrings.
- All phases have documented acceptance criteria.
- Architecture decisions are recorded as ADRs.

### NFR-04: Testability
- Unit test coverage > 80%.
- Integration tests for all API endpoints.
- Agent workflow tests with mocked LLM.
- RAG evaluation with precision/recall metrics.

### NFR-05: Deployability
- Single `docker compose up` starts all services.
- Environment configured via `.env` file.
- Database migrations run automatically on startup.

## Constraints

- Python 3.12+ (backend).
- Node.js 20+ (frontend).
- PostgreSQL 16+ with pgvector extension.
- No Redis, Kafka, or microservices in v1.0.
- All monetary values in CNY (元), stored as DECIMAL(10,2).
- Single-region deployment (no multi-DC).
