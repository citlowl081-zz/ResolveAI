# Phase 05 — Memory System

## Phase Goals

Implement the three-tier memory system: short-term session memory, long-term user memory, and business state memory. Integrate memory operations into the agent state machine's MEMORY_UPDATE node and the session startup flow.

## Preconditions

- Phase 03 completed (agent state machine).
- Phase 04 completed (optional, memory doesn't depend on RAG).

## Task Checklist

### 5.1 Memory Repository
- [ ] `repositories/memory_repository.py` — CRUD for customer_memories table.
- [ ] Filter by user_id, memory_type, key.
- [ ] Upsert logic (update if exists, insert if not).
- [ ] TTL-based expiration for short-term memories.

### 5.2 Short-Term Memory
- [ ] `memory/short_term.py` — Session-scoped memory management.
- [ ] Save/load from LangGraph state (primary).
- [ ] Persist to customer_memories table on checkpoint (secondary).
- [ ] Auto-expire after session TTL.

### 5.3 Long-Term Memory
- [ ] `memory/long_term.py` — User-scoped memory.
- [ ] Summarization via LLM call (session → summary → merge).
- [ ] Preference tracking.
- [ ] Risk profile updates.
- [ ] History compression (keep last N summaries, merge older).

### 5.4 Business State Memory
- [ ] `memory/business_state.py` — Cross-session operational memory.
- [ ] Track active tickets, pending approvals, commitments.
- [ ] Clear fulfilled items.
- [ ] Priority loading on new session start.

### 5.5 Integration
- [ ] MEMORY_UPDATE node: save all three tiers.
- [ ] Session start: load long-term + business state.
- [ ] CUSTOMER_IDENTIFICATION: inject long-term memory into context.
- [ ] FACT_COLLECTION: check business state for existing tickets.
- [ ] ACTION_EXECUTION: update business state after operations.

### 5.6 Session Resume
- [ ] Load agent session from database.
- [ ] Restore LangGraph state from checkpoint.
- [ ] Continue from last node.

### 5.7 Testing
- [ ] Short-term memory: save, load, expire.
- [ ] Long-term memory: summarize, merge, compress.
- [ ] Business state: track, clear, prevent duplicates.
- [ ] Session resume: save state, new session, restore.
- [ ] Memory isolation: user A cannot read user B's memories.
- [ ] Integration: full workflow with memory operations.

## Acceptance Criteria

- [ ] Short-term memory expires after session TTL.
- [ ] Long-term memory persists across sessions.
- [ ] Business state prevents duplicate refunds/reshipments.
- [ ] New session reads existing business state before intent classification.
- [ ] Session can be resumed from checkpoint.
- [ ] Memory is isolated per user_id.
- [ ] All tests pass.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
