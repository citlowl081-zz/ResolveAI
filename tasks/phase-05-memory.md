# Phase 05 — Memory System

## Phase Goals

Implement the three-tier memory system: short-term session memory, long-term user memory, and business state memory. Integrate memory operations into the agent state machine's MEMORY_UPDATE node and the session startup flow.

## Preconditions

- Phase 03 completed (agent state machine).
- Phase 04 completed (optional, memory doesn't depend on RAG).

## Task Checklist

### 5.1 Memory Repository ✅
- [x] `repositories/customer_memory.py` — CRUD for customer_memories table.
- [x] Filter by user_id, memory_type, key.
- [x] Upsert logic (update if exists, insert if not).
- [x] Dedup via get_active_by_key() with partial unique index.

### 5.2 Long-Term Memory ✅
- [x] `models/customer_memory.py` — User-scoped memory model.
- [x] 5 memory types: PREFERENCE / FACT / SUMMARY / COMMITMENT / RISK_PROFILE.
- [x] Preference tracking via explicit "remember" and keyword detection.
- [x] Ticket resolution summarization.
- [x] Merge/dedup by (user_id, memory_type, key).

### 5.3 Agent Integration ✅
- [x] build_context: load active memories with LLM field projection.
- [x] compose_response: _evaluate_memory_changes at every return point.
- [x] Memory decision rules: explicit remember → FACT, multi-turn preference → PREFERENCE, ticket resolution → SUMMARY.
- [x] One-off inquiries (logistics, greetings) excluded from memory.
- [x] Memory data minimization: only memory_type/key/content/confidence sent to LLM.

### 5.4 Privacy & Security ✅
- [x] Sensitive info detection: JWT, bank card, CN ID, API key, password, detailed address.
- [x] Content + structured_data checked before storage.
- [x] Memory write/update/delete records audit_logs.
- [x] Users can view and delete their own memories.
- [x] CUSTOMER-only RBAC on all memory endpoints.

### 5.5 Testing ✅
- [x] CRUD: create, read, update, delete.
- [x] User isolation: user A cannot read user B's memories.
- [x] RBAC: unauthorized, admin, operator access rejected.
- [x] Explicit "remember" triggers write.
- [x] Ordinary chat does NOT trigger write.
- [x] Duplicate key merge/update.
- [x] build_context memory injection.
- [x] Data minimization (field projection).
- [x] Sensitive info rejection.
- [x] Agent memory integration (citation + memory coexistence).
- [x] Audit logging.
- [x] Migration cycle (upgrade → downgrade → upgrade).
- [x] Phase 02–04 regression: 389 passed, 0 failures.

## Acceptance Criteria

- [x] Long-term memory persists across sessions.
- [x] Memory is isolated per user_id.
- [x] Privacy filter rejects sensitive data before storage.
- [x] Audit logs recorded on all mutating operations.
- [x] Agent uses memory for more consistent responses.
- [x] All tests pass.

## Completion Record

- **Started:** 2026-07-15
- **Completed:** 2026-07-15
