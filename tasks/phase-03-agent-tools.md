# Phase 03 — Agent Tools (v10 — Turn Lifecycle & Atomic Release)

## Phase Goals

Implement a fully replayable Agent infrastructure. The `active_turn_*` fields follow a strict lifecycle: they are ONLY cleared atomically with idempotency COMPLETION. Recoverable interruptions preserve turn identity for same-key recovery. State corruption is detected, not guessed.

## Revision History

- **2026-07-14 (v1–v8):** Initial planning through data minimization.
- **2026-07-14 (v9):** Replay consistency + deterministic recovery.
- **2026-07-14 (v10):** Turn lifecycle + atomic release fix:
  - **(1) active_turn ONLY cleared atomically with idempotency COMPLETION.** Two legal paths: success TX-B and terminal error TX-B. Never cleared in crash handler.
  - **(2) Recoverable interruptions preserve turn identity.** active_turn_id, trace_id, key_hash, request_hash, started_at retained. expires_at set to NOW() or kept. Idempotency stays PROCESSING.
  - **(3) STATE_CORRUPTION defined.** PROCESSING + active_turn_id IS NULL → AGENT_TURN_STATE_CORRUPTED → 500. Not auto-recovered.
  - **(4) Different-key cleanup uses application-layer key hash matching.** No pgcrypto, no database SHA256 function.
  - **(5) Exception classification: TERMINAL_ERROR vs RECOVERABLE_INTERRUPTION vs STATE_CORRUPTION.**
  - **(6) 17 error codes:** Added AGENT_TURN_STATE_CORRUPTED.

---

## 0. Service Adapter Matrix

| Service | Method | Signature | Ownership |
|---------|--------|-----------|-----------|
| OrderService | `get_order` | `(order_id, requesting_user_id, role) → dict` | `order.user_id != requesting_user_id → 404` |
| OrderService | `list_my_orders` | `(user_id, page, page_size) → dict` | Auto-scoped |
| LogisticsService | `get_logistics` | `(order_id) → dict` | **None.** Wrapper calls `OrderService.get_order()` first. |
| TicketService | `create_ticket` | `(user_id, order_id, intent, requested_items, customer_request, user_agent) → dict` | `order.user_id == user_id` |
| TicketService | `cancel_ticket` | `(user_id, ticket_id, expected_version, user_agent) → dict` | `ticket.user_id == user_id` |
| TicketService | `get_ticket` | `(ticket_id, requesting_user_id, role) → dict` | `ticket.user_id != requesting_user_id → 404` |
| TicketService | `list_my_tickets` | `(user_id, page, page_size) → dict` | Auto-scoped |

---

## 1. active_turn Lifecycle (Definitive)

### 1.1 State Diagram

```
                    ┌──────────────────┐
                    │  ALL NULL        │ ← No active turn. Session idle.
                    └────────┬─────────┘
                             │ TX-A: atomic acquisition succeeds
                             ▼
                    ┌──────────────────┐
                    │  ALL 6 NON-NULL  │ ← Turn active. turn_id, trace_id,
                    │  expires > now   │   key_hash, request_hash,
                    └──┬──────┬────┬───┘   started_at, expires_at all set.
                       │      │    │
           ┌───────────┘      │    └──────────────┐
           ▼                  ▼                    ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
    │ SUCCESS TX-B │  │ TERMINAL     │  │ RECOVERABLE          │
    │ (atomic)     │  │ ERROR TX-B   │  │ INTERRUPTION         │
    │              │  │ (atomic)     │  │ (preserve identity)  │
    │ • final msgs │  │ • error msgs │  │                      │
    │ • idem=COMP  │  │ • idem=COMP  │  │ • idem=PROCESSING    │
    │ • clear turn │  │ • clear turn │  │ • keep active_turn_* │
    │ • commit     │  │ • commit     │  │ • expires_at = NOW() │
    └──────┬───────┘  └──────┬───────┘  │   (or keep original) │
           │                 │           └──────────┬───────────┘
           ▼                 ▼                      │
    ┌──────────────┐  ┌──────────────┐              │
    │  ALL NULL    │  │  ALL NULL    │              │ Same-key retry:
    │  (idle)      │  │  (idle)      │              │ reads turn_id,
    └──────────────┘  └──────────────┘              │ trace_id from
                                                    │ active_turn_*
                       ┌────────────────────────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  SAME-KEY RETRY  │──► Recover from persisted
              │  (reuses turn_id)│    messages + tool_logs
              └──────────────────┘
                       │
              ┌────────┴─────────┐
              ▼                  ▼
       ┌──────────────┐  ┌──────────────┐
       │ SUCCESS TX-B │  │ DIFFERENT-KEY│
       │ → ALL NULL   │  │ STALE TURN   │
       └──────────────┘  │ CLEANUP      │
                         │ → old turn   │
                         │   AGENT_TURN │
                         │   _EXPIRED   │
                         │ → ALL NULL   │
                         │ → new turn   │
                         │   acquires   │
                         └──────────────┘
```

### 1.2 The One Rule

**active_turn_* fields are ONLY set to NULL atomically with idempotency_records.status = 'COMPLETED'. Never separately. Never in a crash handler that keeps the idempotency record PROCESSING.**

### 1.3 What "Atomic" Means

The UPDATE that clears active_turn_* and the UPDATE that sets idempotency_records.status = 'COMPLETED' must be in the SAME transaction (TX-B). If TX-B rolls back, both stay in their pre-TX-B state: turn identity preserved, idempotency PROCESSING.

---

## 2. Exception Classification

### 2.1 Category A: TERMINAL_ERROR

The exception can be safely converted to a deterministic final response. The same input will always produce the same error. Safe to complete the idempotency record.

| Error | Response |
|-------|----------|
| `BUSINESS_CONFLICT` (non-retryable, deterministic) | 409 with stable error body |
| `ACTION_EXPIRED` | 400 with stable error body |
| `ACTION_ALREADY_CONSUMED` | 409 with stable error body |
| `ACTION_NOT_FOUND` | 400 with stable error body |
| `IDEMPOTENCY_CONFLICT` | 409 with stable error body |
| `SESSION_CLOSED` | 409 with stable error body |
| `AGENT_LOOP_LIMIT` reached | 200 with safe fallback response |
| `TOOL_EXECUTION_FAILED` (non-retryable) | 200 with error summary |
| `INVALID_TOOL_ARGUMENTS` | 200 with error summary |

**Handler (during graph execution, caught by orchestrator):**

```python
async def _handle_terminal_error(self, state, turn_id, trace_id, exc):
    async with self.session_factory() as session:
        # 1. Save final error ASSISTANT or SYSTEM message
        #    (turn_id = stored turn_id, turn_sequence = 100)
        msg = AgentMessage(
            session_id=state["session_id"],
            turn_id=turn_id,
            turn_sequence=100,
            role="ASSISTANT",
            content=_safe_error_message(exc),
            sequence_number=<next global>,
        )
        session.add(msg)

        # 2. Write failure traces for any unrecorded nodes
        await self._persist_failure_traces(session, state, trace_id, exc)

        # 3. Complete API idempotency with stable error response
        idem_service = IdempotencyService(session)
        await idem_service.complete(
            user_id, "agent_message", key,
            response_status=exc.http_status,
            response_body={"code": exc.code, "message": exc.message},
        )

        # 4-8. ATOMIC: clear turn + update session + commit
        await session.execute(
            update(AgentSession)
            .where(AgentSession.id == state["session_id"])
            .where(AgentSession.active_turn_id == turn_id)
            .values(
                active_turn_id=None,
                active_turn_trace_id=None,
                active_turn_idempotency_key_hash=None,
                active_turn_request_hash=None,
                active_turn_started_at=None,
                active_turn_expires_at=None,
                updated_at=func.now(),
            )
        )
        await session.commit()
    # Turn is now ALL NULL. Idempotency is COMPLETED.
```

### 2.2 Category B: RECOVERABLE_INTERRUPTION

Cannot confirm the turn's final state. The same input should retry and may succeed. Turn identity MUST be preserved.

| Scenario | Why Recoverable |
|----------|----------------|
| Process crash (SIGKILL, OOM) | No chance to write anything |
| `asyncio.CancelledError` | Turn may have partially executed |
| LLM timeout with retries exhausted | LLM may succeed on retry |
| Network interruption to LLM provider | Same |
| Tool executed successfully but TX-B not yet committed | Tool result is durable; recovery should reuse it |
| Database connection lost during TX-B | TX-B rolled back; messages/tool_logs from earlier phases are durable |

**Handler:**

```python
async def _handle_recoverable_interruption(self, state, turn_id, trace_id, exc):
    async with self.session_factory() as session:
        # 1. Write failure traces for unrecorded nodes
        await self._persist_failure_traces(session, state, trace_id, exc)

        # 2. PRESERVE turn identity. Set expires_at to NOW() so
        #    different-key requests can clean up after 90s.
        #    Same-key retry will find the turn via active_turn_id.
        await session.execute(
            update(AgentSession)
            .where(AgentSession.id == state["session_id"])
            .where(AgentSession.active_turn_id == turn_id)
            .values(
                active_turn_expires_at=func.now(),  # Expire now for different-key cleanup
                # All other active_turn_* fields PRESERVED:
                #   active_turn_id — unchanged
                #   active_turn_trace_id — unchanged
                #   active_turn_idempotency_key_hash — unchanged
                #   active_turn_request_hash — unchanged
                #   active_turn_started_at — unchanged
                updated_at=func.now(),
            )
        )
        # 3. Idempotency record stays PROCESSING — do NOT complete it
        await session.commit()

    # After this handler:
    # - active_turn_id, trace_id, key_hash, request_hash, started_at: PRESERVED
    # - active_turn_expires_at: NOW() (stale for different-key, but identity intact)
    # - idempotency_records.status: PROCESSING
    # - Same-key retry: reads active_turn_id → recovers turn
    # - Different-key retry: sees expired turn → cleans up (§5)
```

**What is NOT done:**
- active_turn_* fields are NOT set to NULL
- idempotency record is NOT completed
- No SYSTEM message is saved (turn didn't end; it was interrupted)
- turn_id is NOT regenerated

### 2.3 Category C: STATE_CORRUPTION

`idempotency_records.status = 'PROCESSING'` but `active_turn_id IS NULL` on the session.

This should be impossible under correct operation (turn is only cleared atomically with COMPLETION). If observed, it indicates a bug, manual DB intervention, or a race condition that evaded constraints.

**Handler:**

```python
async def _handle_state_corruption(self, session_id, user_id, idempotency_key):
    # Do NOT guess the turn_id.
    # Do NOT read the latest messages and assume they belong to this turn.
    # Do NOT execute any tools.

    async with self.session_factory() as session:
        # Log the corruption
        trace = AgentTrace(
            session_id=session_id,
            turn_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # sentinel
            trace_id=uuid.uuid4(),
            node_name="orchestrator",
            sequence=0,
            is_success=False,
            error_code="AGENT_TURN_STATE_CORRUPTED",
            error_detail={
                "message": "PROCESSING idempotency record found but active_turn_id is NULL",
                "session_id": str(session_id),
                "user_id": str(user_id),
            },
            duration_ms=0,
        )
        session.add(trace)
        await session.commit()

    # Return to caller:
    raise AppError(
        status_code=500,
        code="AGENT_TURN_STATE_CORRUPTED",
        message="Internal state inconsistency detected. Please contact support.",
    )
```

---

## 3. Same-Key Crash Recovery (Final)

### 3.1 TX-A Decision Tree

```
POST /sessions/{id}/messages  (Key: K, Body: B)

IdempotencyService.acquire_or_get_cached(user_id, "agent_message", K, hash(B))
    │
    ├─ None (NEW):  generate turn_id, trace_id → acquire turn → save USER msg → commit → graph
    │
    ├─ Cached (COMPLETED, same hash):  return cached response
    │
    ├─ ConflictError (COMPLETED, different hash):  409 IDEMPOTENCY_CONFLICT
    │
    └─ ConflictError (PROCESSING, same hash):  RECOVERY PATH
           │
           ├─ resource_id → session
           ├─ SELECT session FOR UPDATE
           ├─ Read active_turn_*:
           │
           ├─ active_turn_expires_at >= NOW():
           │     → Turn still running. 409 AGENT_TURN_IN_PROGRESS.
           │
           ├─ active_turn_id IS NOT NULL AND active_turn_expires_at < NOW():
           │     → Verify SHA256(K) == active_turn_idempotency_key_hash
           │     → RECOVER: reuse active_turn_id as turn_id
           │                 reuse active_turn_trace_id as trace_id
           │     → Query messages WHERE turn_id = active_turn_id
           │     → Query tool_logs WHERE turn_id = active_turn_id
           │     → Resume from breakpoint (§3.2)
           │
           └─ active_turn_id IS NULL:
                 → STATE_CORRUPTION (§2.3)
                 → 500 AGENT_TURN_STATE_CORRUPTED
```

### 3.2 Recovery Execution

```
turn_id = active_turn_id            (reused from session row)
trace_id = active_turn_trace_id     (reused from session row)

messages = SELECT * FROM agent_messages
           WHERE session_id = :sid AND turn_id = :turn_id
           ORDER BY turn_sequence

tool_logs = SELECT * FROM agent_tool_logs
            WHERE session_id = :sid AND turn_id = :turn_id

has_user_msg         = any(m.turn_sequence == 0)
has_tool_call_msg    = any(m.turn_sequence == 10)
has_final_msg        = any(m.turn_sequence == 100)
successful_tool_ids  = {tl.tool_call_id for tl in tool_logs if tl.is_success}
failed_retryable     = [tl for tl in tool_logs if not tl.is_success and tl.error_code in RETRYABLE]

if not has_user_msg:
    → INSERT USER (sequence 0)  [UNIQUE guard]
    → Replay from build_context

if has_user_msg and not has_tool_call_msg:
    → Replay from classify_intent (LLM call)
    → TX-P saves tool-call msg (turn_sequence=10)
    → Execute tools

if has_tool_call_msg:
    → Reuse message_id from that row
    → For each planned tool (identified by deterministic tool_call_id):
        if tool_call_id in successful_tool_ids:
            → SKIP Service call. Read tool_output from existing log.
        elif tool_call_id in failed_retryable and retry_count < max:
            → RETRY Service call. INSERT new tool_log (retry_count incremented).
        else:
            → Execute. INSERT new tool_log.
    → Insert TOOL result messages (turn_sequence 20+N)

if has_final_msg:
    → Skip compose_response
    → TX-B: complete idempotency + clear turn + commit
    → Return rebuilt response from stored messages

else:
    → compose_response (LLM)
    → TX-B: save final msg + TOOL msgs + complete idempotency + clear turn + commit
```

---

## 4. Different-Key Stale Turn Cleanup (Final)

### 4.1 Scenario

Request A: turn acquired, USER msg saved, LLM call started, process crashed. active_turn_expires_at is now in the past.

Request B: different Idempotency-Key, same session. TX-A calls turn acquisition:

```sql
UPDATE agent_sessions
SET active_turn_id = :new_turn_id, ...
WHERE id = :session_id
  AND status = 'ACTIVE'
  AND (active_turn_id IS NULL OR active_turn_expires_at < NOW())
RETURNING id, active_turn_id;
```

If the old turn is expired, this UPDATE WOULD succeed (overwriting the old turn). But we must NOT silently overwrite — we must first finalize the old turn.

### 4.2 Cleanup Protocol

The orchestrator detects a stale turn BEFORE attempting its own turn acquisition:

```python
async def _cleanup_stale_turn_if_needed(self, session_factory, session_id, user_id):
    async with session_factory() as session:
        sess = await session.execute(
            select(AgentSession).where(AgentSession.id == session_id).with_for_update()
        )
        sess = sess.scalar_one_or_none()
        if sess is None:
            return  # Session doesn't exist yet (new session path)

        # Check: is there a stale turn?
        if sess.active_turn_id is None:
            return  # No turn to clean up
        if sess.active_turn_expires_at and sess.active_turn_expires_at >= datetime.now(UTC):
            return  # Turn is still active — caller will get 409 from acquisition

        # Stale turn detected. Find its idempotency record.
        # Use APPLICATION-LAYER matching (no pgcrypto, no DB SHA256).
        # Query candidate PROCESSING records for this user + operation.
        idem_records = await session.execute(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.operation == "agent_message",
                IdempotencyRecord.status == "PROCESSING",
            )
        )
        old_record = None
        import hashlib
        for rec in idem_records.scalars().all():
            computed_hash = hashlib.sha256(
                rec.idempotency_key.encode()
            ).hexdigest()
            if computed_hash == sess.active_turn_idempotency_key_hash:
                old_record = rec
                break

        old_turn_id = sess.active_turn_id

        # Complete old idempotency record as AGENT_TURN_EXPIRED
        if old_record is not None:
            old_record.status = "COMPLETED"
            old_record.response_status = 503
            old_record.response_body = {
                "code": "AGENT_TURN_EXPIRED",
                "message": "The previous request timed out. Please retry with a new Idempotency-Key.",
            }
            old_record.completed_at = datetime.now(UTC)

        # Optionally save SYSTEM message for old turn
        sys_msg = AgentMessage(
            session_id=session_id,
            turn_id=old_turn_id,
            turn_sequence=100,
            role="SYSTEM",
            content="Request timed out",
            sequence_number=sess.message_count + 1,
        )
        session.add(sys_msg)
        sess.message_count += 1

        # Clear old active_turn
        sess.active_turn_id = None
        sess.active_turn_trace_id = None
        sess.active_turn_idempotency_key_hash = None
        sess.active_turn_request_hash = None
        sess.active_turn_started_at = None
        sess.active_turn_expires_at = None

        await session.commit()
    # Old turn is now finalized. Caller proceeds with new turn acquisition.
```

### 4.3 No pgcrypto Dependency

The `SHA256()` call is Python's `hashlib.sha256`. The query uses `operation = 'agent_message' AND status = 'PROCESSING'` to get candidate rows (typically 0–2 rows). Application code computes the hash of each candidate's raw `idempotency_key` and compares with `active_turn_idempotency_key_hash`. No database-level hash function is required.

---

## 5. TX-B: The Only Place Turn Is Cleared

### 5.1 Success TX-B

```sql
BEGIN;
  -- Save TOOL result messages (turn_sequence 20+N)
  INSERT INTO agent_messages (...) VALUES (...);

  -- Save final ASSISTANT message (turn_sequence 100)
  INSERT INTO agent_messages (...) VALUES (...);

  -- Consume pending_action in context_snapshot
  UPDATE agent_sessions SET context_snapshot = ...;

  -- Complete API idempotency
  UPDATE idempotency_records
  SET status = 'COMPLETED', response_status = 200, response_body = ..., completed_at = NOW()
  WHERE user_id = :uid AND operation = 'agent_message'
    AND idempotency_key = :key AND status = 'PROCESSING';

  -- Clear active_turn (ATOMIC with above)
  UPDATE agent_sessions
  SET active_turn_id = NULL, active_turn_trace_id = NULL,
      active_turn_idempotency_key_hash = NULL, active_turn_request_hash = NULL,
      active_turn_started_at = NULL, active_turn_expires_at = NULL,
      message_count = :new_count, expires_at = NOW() + INTERVAL '24 hours',
      updated_at = NOW()
  WHERE id = :session_id AND active_turn_id = :turn_id;

COMMIT;
```

If COMMIT fails → entire TX-B rolls back → active_turn preserved, idempotency stays PROCESSING → same-key retry can recover.

### 5.2 Terminal Error TX-B

```sql
BEGIN;
  -- Save error ASSISTANT or SYSTEM message (turn_sequence 100)
  INSERT INTO agent_messages (...) VALUES (...);

  -- Write failure traces for unrecorded nodes
  INSERT INTO agent_traces (...) VALUES (...);

  -- Complete API idempotency with error response
  UPDATE idempotency_records
  SET status = 'COMPLETED', response_status = :error_status,
      response_body = :error_body, completed_at = NOW()
  WHERE user_id = :uid AND operation = 'agent_message'
    AND idempotency_key = :key AND status = 'PROCESSING';

  -- Clear active_turn (ATOMIC with above)
  UPDATE agent_sessions SET active_turn_* = NULL ...;

COMMIT;
```

### 5.3 What NEVER Happens

- active_turn is NEVER cleared in a transaction that doesn't also complete the idempotency record.
- active_turn is NEVER cleared in a "cleanup" handler that leaves idempotency as PROCESSING.
- The crash handler (recoverable interruption) NEVER clears active_turn_* (except setting `expires_at = NOW()`).
- There is NO background job that clears active_turn independently.

---

## 6. Turn Identity Preservation Across Interruption

### 6.1 What's Preserved

After a RECOVERABLE_INTERRUPTION handler runs:

| Field | State |
|-------|-------|
| `active_turn_id` | **Preserved** — original UUID |
| `active_turn_trace_id` | **Preserved** — original UUID |
| `active_turn_idempotency_key_hash` | **Preserved** — SHA-256 of original key |
| `active_turn_request_hash` | **Preserved** — SHA-256 of original body |
| `active_turn_started_at` | **Preserved** — original timestamp |
| `active_turn_expires_at` | **Set to NOW()** — signals staleness to different-key requests |
| `idempotency_records.status` | **PROCESSING** — not completed |
| `agent_messages` (USER, etc.) | **Preserved** — whatever was saved before interruption |
| `agent_tool_logs` | **Preserved** — whatever was saved before interruption |

### 6.2 Why expires_at = NOW()

Setting `expires_at = NOW()` achieves two goals simultaneously:
1. **Different-key requests** see the turn as expired → can trigger cleanup.
2. **Same-key retry** still reads `active_turn_id` and `active_turn_trace_id` from the row — these fields are NOT cleared. The retry logic checks key hash match, not expiry, to authorize recovery.

---

## 7. Error Codes (17 — Final)

| # | Error Code | Category | Retryable | User-Visible | HTTP |
|---|-----------|----------|-----------|--------------|------|
| 1 | `INVALID_TOOL_ARGUMENTS` | TERMINAL | No | No | — |
| 2 | `TOOL_NOT_FOUND` | TERMINAL | No | No | — |
| 3 | `TOOL_FORBIDDEN` | TERMINAL | No | No (WARN) | — |
| 4 | `RESOURCE_NOT_FOUND` | TERMINAL | No | Yes | — |
| 5 | `BUSINESS_CONFLICT` | TERMINAL | No | Yes | — |
| 6 | `IDEMPOTENCY_CONFLICT` | TERMINAL | No | Yes | 409 |
| 7 | `ACTION_EXPIRED` | TERMINAL | No | Yes | 400 |
| 8 | `ACTION_ALREADY_CONSUMED` | TERMINAL | No | Yes | 409 |
| 9 | `ACTION_NOT_FOUND` | TERMINAL | No | Yes | 400 |
| 10 | `TOOL_TIMEOUT` | RECOVERABLE | Yes (1×) | Only if exhausted | — |
| 11 | `TOOL_EXECUTION_FAILED` | TERMINAL | No | Yes | — |
| 12 | `LLM_ERROR` | RECOVERABLE | Yes (1×) | Only if exhausted | — |
| 13 | `AGENT_LOOP_LIMIT` | TERMINAL | No | No (logged) | — |
| 14 | `SESSION_CLOSED` | TERMINAL | No | Yes | 409 |
| 15 | `AGENT_TURN_IN_PROGRESS` | N/A (retry later) | No | Yes | 409 |
| 16 | `AGENT_TURN_EXPIRED` | TERMINAL (old key) | No | Yes (old key) | 503 |
| 17 | `AGENT_TURN_STATE_CORRUPTED` | CORRUPTION | No | No (generic 500) | 500 |

**Category legend:**
- **TERMINAL:** Can be atomically completed with idempotency COMPLETION + turn clear.
- **RECOVERABLE:** Preserves turn identity. Same-key retry recovers. Different-key cleanup handles staleness.
- **CORRUPTION:** No automatic recovery. Human or maintenance task intervention.
- **N/A:** Not an error in the turn lifecycle sense — the turn is running, try again later.

---

## 8. Test Plan Additions (v10)

### 8.1 New Tests

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_turn_lifecycle.py::test_recoverable_preserves_active_turn_id` | After RECOVERABLE_INTERRUPTION handler, active_turn_id is NOT NULL |
| 2 | `test_turn_lifecycle.py::test_recoverable_preserves_active_turn_trace_id` | active_turn_trace_id is NOT NULL after interruption |
| 3 | `test_turn_lifecycle.py::test_recoverable_preserves_idempotency_processing` | idempotency_records.status = 'PROCESSING' after interruption |
| 4 | `test_turn_lifecycle.py::test_same_key_recovers_from_preserved_turn_id` | Same-key retry reuses preserved active_turn_id |
| 5 | `test_turn_lifecycle.py::test_success_txb_atomic_idempotency_and_turn_clear` | In one tx: idempotency COMPLETED AND active_turn NULL |
| 6 | `test_turn_lifecycle.py::test_terminal_error_atomic_idempotency_and_turn_clear` | Terminal error: both happen in same tx |
| 7 | `test_turn_lifecycle.py::test_txb_rollback_preserves_turn` | TX-B fails after saving msgs → active_turn still set, idempotency still PROCESSING |
| 8 | `test_turn_lifecycle.py::test_processing_with_null_active_turn_returns_corrupted` | STATE_CORRUPTION → 500, no auto-recovery |
| 9 | `test_turn_lifecycle.py::test_different_key_matches_by_application_hash` | Python hashlib comparison, no pgcrypto |
| 10 | `test_turn_lifecycle.py::test_different_key_cleanup_no_database_hash_dependency` | Verify no pgcrypto or DB SHA256 in query |
| 11 | `test_phase02_regression.py::test_all_49_phase02_tests_pass` | Full Phase 02 regression |

### 8.2 Updated Test File Inventory (22 files)

```
backend/tests/unit/test_llm_adapter.py
backend/tests/unit/test_tool_schema.py
backend/tests/unit/test_tool_registry.py
backend/tests/unit/test_tool_executor.py
backend/tests/unit/test_nodes.py
backend/tests/unit/test_routing.py
backend/tests/unit/test_loop_limit.py
backend/tests/unit/test_tool_call_id.py
backend/tests/unit/test_pending_action.py
backend/tests/integration/test_agent_api.py
backend/tests/integration/test_agent_rbac.py
backend/tests/integration/test_agent_idempotency.py
backend/tests/integration/test_agent_concurrency.py
backend/tests/integration/test_agent_errors.py
backend/tests/integration/test_agent_trace.py
backend/tests/integration/test_agent_tool_log.py
backend/tests/integration/test_agent_context.py
backend/tests/integration/test_agent_pii.py
backend/tests/integration/test_agent_migration.py
backend/tests/integration/test_agent_recovery.py
backend/tests/integration/test_agent_active_turn.py
backend/tests/integration/test_agent_turn_lifecycle.py     (NEW)
backend/tests/integration/test_phase02_regression.py
```

---

## 9. Acceptance Criteria

- [ ] active_turn cleared ONLY in TX-B (success or terminal error) — atomically with idempotency COMPLETION
- [ ] RECOVERABLE_INTERRUPTION handler preserves active_turn_id, trace_id, key_hash, request_hash, started_at
- [ ] RECOVERABLE_INTERRUPTION handler keeps idempotency PROCESSING
- [ ] Same-key retry reads turn_id + trace_id from preserved active_turn_* fields
- [ ] Same-key retry recovery succeeds from persisted messages + tool_logs
- [ ] Different-key stale turn cleanup uses application-layer SHA-256 matching (no pgcrypto)
- [ ] STATE_CORRUPTION (PROCESSING + active_turn_id IS NULL) → 500, no guessing
- [ ] TX-B rollback does NOT clear active_turn (both roll back together)
- [ ] 17 error codes defined and categorized (TERMINAL/RECOVERABLE/CORRUPTION)
- [ ] Phase 02 regression: all 49 existing tests pass unchanged
- [ ] ~100 tests pass on fresh DB with LLM_PROVIDER=mock
- [ ] CI passes without LLM_API_KEY
- [ ] Ruff 0, Mypy 0

## Completion Record

- **Started:** TBD
- **Completed:** TBD
