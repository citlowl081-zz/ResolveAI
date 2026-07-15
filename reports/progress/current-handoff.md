# ResolveAI — Current Handoff

**Date:** 2026-07-15
**Generated:** After Phase 06 completion
**Updated:** Phase 06 COMPLETE — Human approval system with risk-based escalation, optimistic locking, payload integrity

---

## Current Phase

**Phase 06 — Human-in-the-Loop: COMPLETE**

Phase 06 is fully implemented. 424 tests pass with zero regressions.
Key deliverables: ApprovalTask model with 5 approval types, Migration 007, Admin approval API (list/approve/reject/execute) with CUSTOMER self-view, Agent orchestrator approval gate before graph execution, optimistic locking for concurrent decisions, payload integrity (DB-stored, not client-submitted), audit logging, 35 new tests.
Next phase: Phase 07 — Frontend (not started).

---

## Completed Content

### Phase 00 — Planning
- Complete project documentation (12 design docs + 4 ADRs)
- Task tracking for all 10 phases
- Directory structure

### Phase 01 — Project Foundation
- FastAPI app factory with CORS, lifespan, exception handlers
- Async SQLAlchemy engine, session, Base + TimestampMixin
- `GET /health` endpoint, Alembic migration 001
- PostgreSQL 16 + pgvector via Docker Compose
- Next.js 14 customer-web + admin-web scaffolds
- GitHub Actions CI pipeline

### Phase 02A — Core Commerce Backend
- 8 tables, 5 enums, 18 API endpoints
- JWT auth (access/refresh with type enforcement), RBAC
- Order lifecycle (create→pay→ship→deliver→cancel)
- Idempotency via INSERT ON CONFLICT DO NOTHING RETURNING
- 33 self-contained tests, CI green

### Phase 02B — After-sales Business Backend
- 3 new tables, 5 new enums, 2 sequences, order_status +REFUNDED
- 13 API endpoints (4 customer + 9 operator/admin)
- Eligibility engine (7 reject codes), deterministic refund calculator
- Lock ordering: ticket→order→order_items→products
- Cumulative refund cap, cross-key duplicate guard
- 16 new integration tests (49 total), CI green

### Phase 03 — Agent Tools
- **LangGraph:** 9 nodes with declarative routing. ModelProvider ABC (AnthropicProvider + MockProvider). classify_intent and compose_response use LLM primary path with keyword/template fallback.
- **Tools:** 7 customer-facing tools wrapping Phase 02 Services. Write tools via pending_action→confirm_action_id. allowed_roles={UserRole.CUSTOMER}.
- **Database:** 4 new tables (agent_sessions, agent_messages, agent_tool_logs, agent_traces) + 2 enums. Migration 004 with active_turn CHECK constraint.
- **Turn Lifecycle:** 6 active_turn_* columns. Atomic acquisition + atomic release (TX-B only). RECOVERABLE_INTERRUPTION preserves turn identity. STATE_CORRUPTION handled.
- **Idempotency:** API-level via Idempotency-Key header. Tool-level via SHA256 (no date, no trace_id). bind_resource() early session binding.
- **Trace & Observability:** Per-node agent_traces. agent_tool_logs with message_id + tool_call_id linkage. PII sanitization across all logs.
- **API:** 10 endpoints (6 customer + 4 admin). Sync HTTP only.
- **LLM Data Minimization:** Field allowlists. Shipping address removed entirely. No user_id, email, JWT sent to external LLM.
- **Tests:** 155 passed (49 Phase02 + 12 Agent API + 54 AnthropicProvider + 25 Verification + 15 Recovery/Transactions). LLM_PROVIDER=mock, zero real API keys.
- **Quality:** Ruff PASS (app/ + tests/). Mypy PASS (143 source files, 0 errors). Pip check PASS. Migration cycle PASS.
- **GitHub Actions:** Backend Lint & Typecheck PASS. Backend Tests PASS (155/155). Frontend builds PASS.

---

## Project Structure

```
ResolveAI/
├── backend/               # Python FastAPI backend (unified API server)
│   ├── app/
│   │   ├── agent/          # LangGraph state machine (9 nodes)
│   │   ├── llm/            # ModelProvider ABC + Anthropic + Mock
│   │   ├── tools/          # 7 customer-facing Agent tools
│   │   ├── api/v1/         # 41 API endpoints total
│   │   ├── models/         # 16 SQLAlchemy models
│   │   ├── repositories/   # 18 async repositories
│   │   └── services/        # 12 service classes
│   ├── alembic/            # 4 migrations (001–004)
│   └── tests/              # 155 tests
├── frontend/
│   ├── customer-web/       # Next.js 14 customer portal
│   └── admin-web/          # Next.js 14 admin panel
├── miniprogram/            # WeChat Mini Program (planned Phase 07)
├── docs/                   # Architecture & design documents
├── tasks/                  # Phase-based task tracking
├── reports/                # Progress reports
└── .github/workflows/      # CI pipeline
```

---

## API Endpoints: 41

### Phase 02A (18)
- 4 Auth, 4 Products, 7 Orders, 2 Logistics, 1 Admin

### Phase 02B (13)
- 4 Customer after-sales, 9 Operator/Admin after-sales + reshipments

### Phase 03 (10)
- 6 Customer Agent: sessions CRUD, messages, close
- 4 Admin Agent: traces and tool logs inspection

---

## Database: 16 Tables, 12 Enums

Phase 02: 12 tables, 10 enums
Phase 03: +4 tables (agent_sessions, agent_messages, agent_tool_logs, agent_traces), +2 enums (session_status, message_role)

---

## Latest Commits (on origin/main)

```
0e3be55 [Chore] Add standalone miniprogram directory
bbce85a [CI] Isolate MockProvider and stabilize tool log test
b53d1ff [CI] Install Phase 03 runtime dependencies in backend tests
28b126c [Phase 03] Fix test typing and finalize release verification
24b9dea [Phase 03] Complete recovery, transaction, and action verification
```

---

## Key Architecture Decisions

1. **Transaction ownership:** get_db commits on success, rolls back on exception. Services flush only.
2. **Idempotency:** Single idempotency_records table. No idempotency_key on business tables.
3. **Optimistic locking:** version column on all mutating entities.
4. **Lock ordering:** ticket→order→order_items(by id ASC)→products(by product_id ASC).
5. **Partial refund = no order status change.** Only full refund→REFUNDED.
6. **Agent TX boundaries:** Short UoW. No DB connections during LLM calls.
7. **Write tools not auto-executed:** pending_action + confirm_action_id mechanism.
8. **Active turn lock:** Persistent columns, atomic acquisition, never held across I/O.
9. **LLM data minimization:** Field allowlists applied at 3 points.
10. **Web + Mini Program share backend:** Single API server, no per-client forks.

---

## Known Limitations

1. No payment gateway — payment/refund are simulated
2. No RAG, no policy_documents, no vector search (Phase 04)
3. No long-term memory (Phase 05)
4. No human-in-the-loop (Phase 06)
5. No WebSocket/SSE (Phase 07)
6. No Redis, no Kafka, no microservices (by design)

---

## Next Task

**Phase 04A — Policy Knowledge Base** (implementation not started).
**Phase 04B — Agent RAG Integration** (not started).
**Phase 04C — PDF/DOCX Upload** (not started, deferred).

Phase 04 plan in `tasks/phase-04-rag.md` (revision 4, approved). Key design decisions:
- `policy_key` + `version` model (UNIQUE(policy_key, version), one ACTIVE per key, advisory lock for concurrency)
- `policy_key` validated against explicit prefix set (RET/REF/EXC/RES/LOG/RISK/SOP/GEN), prefix consistent with category
- Status API targets exact (policy_key, version): `PATCH .../versions/{version}/status`
- `GET /by-key/{key}` returns ACTIVE only (404 if none)
- Ingestion idempotency compares against latest version (not just ACTIVE)
- No new LangGraph node — uses existing tool-execution path
- Chinese-friendly chunking + BLAKE2b bigram feature-hash mock embeddings
- Exact cosine search (no IVFFlat), embedding TX boundary safety
- YAML frontmatter (metadata) + body text (content); `effective_date` required
- 04A = KB + retrieval, 04B = agent + eval, 04C = PDF/DOCX (optional)

See `tasks/active-phase.md` for current phase pointer.

---

## Start & Test Commands

```bash
# PostgreSQL
docker compose up -d db

# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Full check
ruff check app/ tests/
mypy --no-incremental app/ tests/
LLM_PROVIDER=mock DATABASE_URL="postgresql+asyncpg://resolveai:resolveai-dev@localhost:5432/resolveai_test" pytest -v

# Frontend
cd frontend/customer-web && npm run dev   # :3000
cd frontend/admin-web && npm run dev      # :3001
```
