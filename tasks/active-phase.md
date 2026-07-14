# Active Phase

**Current Phase:** Phase 04A — Policy Knowledge Base (Batch 1 COMPLETE)

**Previous Phase:** Phase 03 — Agent Tools (COMPLETE)

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

## Phase 04 Status: IN PROGRESS

Phase 04 implementation plan approved (revision 4). See `tasks/phase-04-rag.md` for the complete plan.

Phase 04 is split into:
- **04A** — Policy Knowledge Base (data model, embeddings, chunking, ingestion, retrieval, admin API)
- **04B** — Agent RAG Integration (tool, citations, evaluation) — **not started**
- **04C** — PDF/DOCX Upload (optional, deferred) — **not started**

### Phase 04A Batch 1 — COMPLETE
- Python enums: PolicyCategory, PolicyStatus with `from_prefix()` lookup
- policy_key validation: `validate_policy_key()`, `validate_policy_key_and_category()` in `app/rag/validation.py`
- Settings: embedding config (OpenAI-compatible `EMBEDDING_PROVIDER/MODEL/API_KEY/BASE_URL/DIMENSION/TIMEOUT_SECONDS/MAX_RETRIES` + `RAG_TOP_K` + `RAG_MIN_SIMILARITY`)
- SQLAlchemy models: PolicyDocument (policy_key + version keyed), PolicyChunk (vector(1536))
- Migration 005: policy_documents + policy_chunks tables with all constraints and indexes
- Tests: 49 new (20 unit + 13 integration model constraints). Total: 204 passed. Zero regressions.

### Phase 04A Remaining
- Batch 2: Embedding providers (ABC, Mock, OpenAI-compatible), chunking, content_hash
- Batch 3: Repositories, retrieval (exact cosine search)
- Batch 4: PolicyService, ingestion, admin API
- Batch 5: Policy data files (14 markdown policies)

**Phase 04A is NOT complete.** Phase 04B and 04C have NOT started.

## Next Step

Phase 04A Batch 2: EmbeddingProvider ABC, MockEmbeddingProvider (BLAKE2b bigram), OpenAICompatibleEmbeddingProvider (httpx), Chinese-friendly chunking, content_hash function.
