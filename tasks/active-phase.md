# Active Phase

**Current Phase:** Phase 03 — Agent Tools (FINAL TURN LIFECYCLE FIX — v10)

**Previous Phase:** Phase 02 — Business Backend ✅ (COMPLETE, Remote CI Verified)

## Phase 02 Status: ✅ COMPLETE

### Phase 02A — Core Commerce Backend ✅
- 8 tables, 5 enums, 18 API endpoints. JWT auth with RBAC, order lifecycle.
- 33 self-contained tests, CI green. Completed: 2026-07-13.

### Phase 02B — After-sales Business Backend ✅
- 3 new tables, 5 new enums, 2 sequences, order_status extension.
- 13 API endpoints. Cumulative refund cap, lock ordering, cross-key dedup.
- 16 new integration tests (49 total), CI green. Completed: 2026-07-14.

## Phase 03 — Agent Tools (Final Planning — v10)

Turn lifecycle + atomic release fix. Awaiting user approval.

- **Turn Lifecycle:** active_turn_* ONLY cleared atomically with idempotency COMPLETION. Two legal clear paths: success TX-B and terminal error TX-B. Never cleared in crash handler.
- **Exception Classification:** TERMINAL_ERROR (atomic complete+clear), RECOVERABLE_INTERRUPTION (preserve turn identity, keep idempotency PROCESSING), STATE_CORRUPTION (500, no guessing).
- **Same-Key Recovery:** Reuses active_turn_id + active_turn_trace_id from preserved row. Recovers from persisted messages + tool_logs.
- **Different-Key Cleanup:** Application-layer SHA-256 key hash matching. No pgcrypto dependency.
- **State Corruption:** PROCESSING + active_turn_id IS NULL → AGENT_TURN_STATE_CORRUPTED → 500.
- **17 Error Codes:** Added AGENT_TURN_STATE_CORRUPTED (#17).
- **~100 Tests:** 22 test files. Phase 02 regression must pass unchanged.

## Sub-Phase Documents

- [Phase 02A — Core Commerce Backend](phase-02A-core-commerce.md) ✅
- [Phase 02B — After-sales Business Backend](phase-02B-after-sales.md) ✅
- [Phase 02 — Business Backend (Index)](phase-02-business-backend.md) ✅
- [Phase 03 — Agent Tools](phase-03-agent-tools.md) 📋 (v7 final planning)

## Sub-Phase Documents

- [Phase 02A — Core Commerce Backend](phase-02A-core-commerce.md) ✅
- [Phase 02B — After-sales Business Backend](phase-02B-after-sales.md) ✅
- [Phase 02 — Business Backend (Index)](phase-02-business-backend.md) ✅
- [Phase 03 — Agent Tools](phase-03-agent-tools.md) 📋 (planning complete)
