# Active Phase

**Current Phase:** Phase 07 — Frontend (COMPLETE)

**Previous Phase:** Phase 06 — Human-in-the-Loop (COMPLETE)
**Next Phase:** Phase 08 — Evaluation & Observability (Not started)

## Phase 05 Status: ✅ COMPLETE

- **Data Model:** CustomerMemory (user_id, memory_type, key, content, structured_data, source, confidence, status, superseded_by, version), MemoryType enum (PREFERENCE/FACT/SUMMARY/COMMITMENT/RISK_PROFILE), MemoryStatus enum (ACTIVE/ARCHIVED/SUPERSEDED)
- **Migration:** 006 — customer_memories table with partial unique index on (user_id, memory_type, key) WHERE status='ACTIVE', CASCADE on user delete, upgrade/downgrade cycle verified
- **Repository:** CustomerMemoryRepository — CRUD, get_active_by_key (dedup), get_active_for_context (LLM injection), list_by_user (paginated + filtered)
- **Service:** MemoryService — create/merge, get/list, update, delete; privacy filter (JWT/card/ID/API/password/address detection); audit logging on every mutating operation
- **API:** 5 customer-scoped endpoints (POST/GET/GET{id}/PATCH/DELETE /api/v1/memories), CUSTOMER-only RBAC, user isolation, type/status filters
- **Agent Integration:** build_context loads active memories with LLM field projection (memory_type/key/content/confidence only); compose_response evaluates memory writes at every return point
- **Memory Decision Rules:** Explicit "记住"/"帮我记" → FACT, multi-keyword preferences in turn ≥2 → PREFERENCE, single preference in turn ≥3 → PREFERENCE, ticket resolution → SUMMARY; one-off inquiries/greetings rejected by should_not_save()
- **Privacy:** Regex-based sensitive info detection (JWT, bank card, CN ID, API key, password, detailed address); content + structured_data checked before storage
- **Tests:** 77 new tests (40 unit + 28 integration + 9 agent integration), 389 total (0 failures)
- **Quality:** pip check PASS, ruff PASS, mypy PASS (188 source files, 0 errors), migration downgrade→upgrade PASS

## Phase 06 Status: ✅ COMPLETE

- **Data Model:** ApprovalTask (user_id, action_id UNIQUE, tool_name, sanitized_action_payload JSONB, approval_type, status, risk_level, reason, requested_by, decided_by, decision_reason, expires_at, version), ApprovalStatus enum (PENDING/APPROVED/REJECTED/EXPIRED/CANCELLED), ApprovalType enum (HIGH_REFUND/RISK_HIT/EXCHANGE/MULTI_ITEM/MANUAL_REQUEST)
- **Migration:** 007 — approval_tasks table with indexes on user_id, status, (user_id+status), action_id UNIQUE, version CHECK ≥1, upgrade/downgrade cycle verified
- **Repository:** ApprovalTaskRepository — CRUD, decide() with optimistic locking (version + status check), expire_pending()
- **Service:** ApprovalService — idempotent create_approval(), approve()/reject() with state validation + optimistic locking, list_tasks()/list_user_tasks()
- **Trigger Rules:** check_approval_required() — HIGH_REFUND (>threshold), RISK_HIT (HIGH risk_level), EXCHANGE (always), MULTI_ITEM (>1 item); threshold from system_configs
- **Agent Integration:** Orchestrator.run() checks approval BEFORE graph execution; if triggers match → creates ApprovalTask, releases turn, returns PENDING_APPROVAL; execute_approved_action() re-runs tool from stored payload
- **API:** Admin — GET/POST approve/POST reject/POST execute `/api/v1/admin/approvals` (OPERATOR/ADMIN); Customer — GET list/GET detail `/api/v1/approvals`; All decide endpoints require Idempotency-Key
- **Payload Integrity:** execute endpoint loads sanitized_action_payload from DB — client cannot inject alternative payload
- **9-node LangGraph preserved:** Approval check happens before graph invocation, not as a new node
- **Tests:** 35 new tests (10 unit + 16 integration + 9 agent integration), 424 total (0 failures)

## Phase 07A Status: ✅ COMPLETE (Customer Web + Admin Web)

- **Customer Web:** 10 pages — Login, Register, Home, Products (list+detail), Orders (list+detail), Agent Chat (messages+citations+actions+approval+confirm), Tickets (list+cancel), Memories (CRUD), Approvals (list)
- **Admin Web:** 8 pages — Login, Dashboard (ticket count+pending approvals), Tickets (list+filter+paginate), Approvals (list+approve+reject+execute), Policies (list), Traces (table+paginate), Tool Logs (table+paginate)
- **Shared Foundation:** APIResponse envelope types, API client with auth header+token refresh+401 handling, AuthContext with login/register/logout, Navbar with navigation, Tailwind responsive layout
- **API Integration:** All pages call real backend endpoints via fetch; no static mock data; NEXT_PUBLIC_API_BASE_URL configurable
- **UI:** Tailwind CSS, same visual language across both apps, loading/empty/error states on all pages, citations displayed with policy_key+version+similarity, approval status color-coded, confirmation dialog for agent actions

### Phase 07A Customer Web Pages

| Page | Route | Features |
|---|---|---|
| Login | /login | Email/password, error state |
| Register | /register | Email/password/name |
| Home | / | Auth gate, nav cards |
| Products | /products | List from API |
| Product Detail | /products/[id] | Detail view |
| Orders | /orders | List with status badges |
| Order Detail | /orders/[id] | Items, logistics |
| Agent Chat | /agent | Messages, citations, actions, approval, confirm/decline |
| Tickets | /tickets | List, cancel |
| Memories | /memories | CRUD with create form |
| Approvals | /approvals | List with status |

### Phase 07A Admin Web Pages

| Page | Route | Features |
|---|---|---|
| Login | /login | Admin auth gate |
| Dashboard | / | Ticket count, pending approvals, nav |
| Tickets | /tickets | List, status filter, paginate |
| Approvals | /approvals | List, approve, reject, execute |
| Policies | /policies | List with version/status |
| Traces | /traces | Table, paginate |
| Tool Logs | /tool-logs | Table, paginate |

- **Build:** Both apps `next build` PASS (0 type errors)

### Phase 07B — WeChat Mini Program ✅

- **12 pages:** login, register, index (home with 6 nav cards), products (list+detail), orders (list+detail with logistics), agent (messages+citations+actions+approval+confirm/decline), tickets (list+cancel), memories (CRUD), approvals (list), profile (logout)
- **API client:** wx.request wrapper with auth header, token refresh, 401 → login redirect, unified error handling
- **Global state:** app.globalData for accessToken/refreshToken/userInfo/apiBase
- **UI:** Global WXSS class library (card, btn, badge, flex-row, etc.), blue theme matching Customer Web, loading/empty/error states on all pages
- **24 files** (4 per page: wxml+ts+json+wxss) + app.ts + app.js + app.json + app.wxss + services/api.ts + utils/util.ts + typings/types.d.ts

### Phase 07B Agent Chat Features

| Feature | Implementation |
|---|---|
| Messages | scroll-view with user (blue right) / assistant (white left) bubbles |
| Citations | Policy key, version, title displayed below assistant messages |
| Proposed actions | Blue info box below message + confirm/cancel button bar |
| PENDING_APPROVAL | Yellow warning box with approval type and status |
| Error handling | System message shown on API failure |
| Empty state | Welcome screen with guidance text |

## Phase 07 Overall: ✅ COMPLETE

All three frontends implemented:
- **Customer Web:** 13 routes, Next.js 14 + Tailwind, builds with 0 type errors
- **Admin Web:** 9 routes, Next.js 14 + Tailwind, builds with 0 type errors
- **WeChat Mini Program:** 12 pages, native TypeScript framework, 36 source files
- **API integration:** 100% real backend API, no static mock data
- **Configuration:** .env.example for Web apps, project.config.example.json for miniprogram

## Phase 03 Status: ✅ COMPLETE

- **LangGraph:** 9 functional nodes (receive_message → load_session → build_context → classify_intent → select_tools → authorize_tool → execute_tool → handle_tool_error → compose_response). persist_messages placeholder removed.
- **ModelProvider:** Abstract ABC with AnthropicProvider + MockProvider. Provider injected via AgentOrchestrator constructor. classify_intent and compose_response use LLM primary path with keyword/template fallback.
- **Tools:** 7 customer-facing tools wrapping Phase 02 Services. Write tools via pending_action → confirm_action_id flow. allowed_roles = {UserRole.CUSTOMER}.
- **Database:** 4 new tables (agent_sessions, agent_messages, agent_tool_logs, agent_traces) + 2 new enums (session_status, message_role). Migration 004 with active_turn CHECK constraint, partial unique indexes.
- **Turn Lifecycle:** 6 active_turn_* columns. Atomic acquisition (WHERE active_turn_id IS NULL). Atomic release only in TX-B (success or terminal error). RECOVERABLE_INTERRUPTION preserves turn identity.
- **Idempotency:** API-level via Idempotency-Key header. Tool-level via SHA256(session_id + action_id + tool_name + canonical_hash). bind_resource() early session binding.
- **Trace:** Per-node persistence via node_timings in complete_turn(). Failed nodes traced with is_success=false. trace_id uses PostgreSQL UUID type.
- **API:** 10 endpoints (6 customer + 4 admin). Sync HTTP only.
- **Tests:** 155 passed (49 Phase 02 + 12 Agent API + 54 AnthropicProvider + 25 Verification + 15 Recovery/Transactions). LLM_PROVIDER=mock only. Zero real API keys.
- **Quality:** Pip check PASS. Ruff PASS. Mypy PASS (app/ + tests/, 143 source files, 0 errors).
- **GitHub Actions:** All green after CI dependency fix (langgraph + anthropic declared in pyproject.toml, LLM_PROVIDER=mock in test job).

## Directory Structure

```
ResolveAI/
├── backend/               # Unified Python FastAPI backend
├── frontend/
│   ├── customer-web/      # Next.js customer frontend
│   └── admin-web/         # Next.js admin frontend
├── miniprogram/           # WeChat Mini Program (planned Phase 07)
├── docs/                  # Architecture & design
├── tasks/                 # Phase task files
└── reports/               # Progress reports
```

## Sub-Phase Documents

- [Phase 02A — Core Commerce Backend](phase-02A-core-commerce.md) ✅
- [Phase 02B — After-sales Business Backend](phase-02B-after-sales.md) ✅
- [Phase 02 — Business Backend (Index)](phase-02-business-backend.md) ✅
- [Phase 03 — Agent Tools](phase-03-agent-tools.md) ✅

## Phase 04 Status: ✅ COMPLETE

Phase 04 implementation plan approved (revision 4). See `tasks/phase-04-rag.md` for the complete plan.

### Phase 04A — Policy Knowledge Base ✅
- Data model: PolicyDocument (policy_key + version), PolicyChunk (vector(1536)), Migration 005
- Embedding: EmbeddingProvider ABC, MockEmbeddingProvider (BLAKE2b unigram+bigram), OpenAICompatibleEmbeddingProvider (httpx)
- Chunking: Chinese-friendly sentence-boundary, content_hash, 3-phase ingestion with advisory locks
- Retrieval: pgvector exact cosine, category/status/date in SQL, dedup per policy_key
- Admin API: 7 CRUD endpoints + 1 upload endpoint (PDF/DOCX), 14 seed policies
- 298 tests at 04A completion

### Phase 04B — Agent RAG Integration ✅
- `search_after_sales_policy` Agent tool (CUSTOMER only), 9-node graph unchanged
- Structured citations from real tool_results, LLM data minimization
- RAG eval: 21 queries, HitRate@5=0.952, Precision@1=0.667, MRR=0.775, zero fabrication
- 312 tests at 04B completion

### Phase 04C — PDF/DOCX Upload ✅
- PDF (pypdf) and DOCX (python-docx) parsing, upload endpoint with size/MIME/extension validation
- Path traversal prevention, controlled error messages, reuses existing ingestion pipeline
- 312 tests total (Phase 04C adds infrastructure, no standalone eval test file)

## Next Step

Phase 08 — Evaluation & Observability (Not started). Do NOT begin until Phase 07 is committed and pushed with CI green.
