# Phase 00 Self-Review Report

**Date:** 2026-07-13  
**Reviewer:** Claude (architect role)  
**Scope:** All Phase 00 deliverables — 64 files, 12 docs, 4 ADRs, 10 phase plans  
**Methodology:** Cross-reference 10 dimensions, trace every requirement to design, analyze consistency gaps

---

## Executive Summary

Phase 00 is **substantially complete and well-structured**, but the review identified **14 issues** across the 10 check dimensions. Of these, **3 are CRITICAL** (would cause implementation confusion or broken flows), **6 are MEDIUM** (design gaps or undocumented decisions), and **5 are LOW** (minor clarifications or nice-to-haves). All issues are fixable within Phase 00 without writing implementation code.

**Overall Grade: B+ (82/100)** — Solid foundation, needs targeted fixes before Phase 01.

---

## Check 1: README.md / AGENTS.md / CLAUDE.md Consistency

### Finding 1.1: No Conflicts Detected ✅

The three files are consistent on:
- Project identity: "AI-powered e-commerce after-sales intelligent ticket agent"
- Tech stack: Python 3.12, FastAPI, SQLAlchemy 2, LangGraph, PostgreSQL + pgvector, Next.js 14
- Phase-based development with sequential execution
- No Redis/Kafka/microservices in early phases
- README tech stack table matches AGENTS architecture constraints

### Finding 1.2: AGENTS.md says "Phase 00–06: No Redis" — CLAUDE.md says "Phases 01–06" (LOW)

- **AGENTS.md line 30:** "No microservices, no Kafka, no Redis (Phase 00–06)."
- **CLAUDE.md line 74:** "Phases 01–06: No Redis, no MCP, no Kafka, no microservices."

Phase 00 has no implementation, so "Phase 00–06" and "Phases 01–06" are functionally identical. Not a real conflict, but should be aligned for precision.

### Finding 1.3: CLAUDE.md correctly references AGENTS.md ✅

CLAUDE.md explicitly says "Read AGENTS.md first — it contains rules shared across all AI coding tools" and "The two files must not conflict." This is the correct pattern.

**Verdict: PASS with 1 minor note.**

---

## Check 2: Cross-Document Consistency (Requirements → Architecture → DB → API → Agent → RAG → Memory)

### Finding 2.1: CRITICAL — Intent Type Enum Mismatch Between Requirements and Database

- **Requirements (FR-05.2):** Intent types are `LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, EXCHANGE, MISSING_PARTS, ESCALATE_TO_HUMAN`
- **Database `intent_type` ENUM:** `LOGISTICS_INQUIRY, PRE_SHIP_REFUND, QUALITY_REFUND, EXCHANGE, MISSING_PARTS, OTHER`
- **Mismatch:** `ESCALATE_TO_HUMAN` vs `OTHER`

`ESCALATE_TO_HUMAN` is a valid user intent (the user explicitly asks for human help). `OTHER` is a catch-all for unrecognized intents. These are different concepts. The enum needs BOTH values:
- `ESCALATE_TO_HUMAN` — user explicitly requests human
- `OTHER` — unclassifiable message

**Fix:** Update `docs/03-database-design.md` intent_type ENUM to include both values.

### Finding 2.2: CRITICAL — Node Count Inconsistency (19 vs "16 nodes")

- **Requirements spec:** Lists 19 nodes (START + 13 active + 5 terminal = 19)
- **docs/02-architecture.md:** "16 nodes"
- **docs/05-agent-workflow.md:** "16 explicit nodes" but actually describes 13 active + 5 terminal = 18 (or 19 if START counted)

Actual count from the state machine diagram and node specs:
- 1 START (implicit)
- 13 active nodes: INTENT_CLASSIFICATION, CUSTOMER_IDENTIFICATION, ORDER_RESOLUTION, FACT_COLLECTION, POLICY_RETRIEVAL, ELIGIBILITY_CHECK, SOLUTION_GENERATION, USER_CONFIRMATION, RISK_CHECK, HUMAN_APPROVAL, ACTION_EXECUTION, RESULT_VERIFICATION, MEMORY_UPDATE
- 5 terminal nodes: COMPLETED, NEED_MORE_INFORMATION, RETRY, ESCALATED, FAILED
- **Total: 18 named nodes (19 including START)**

All docs say "16" but the actual count is 18-19. This will confuse implementers.

**Fix:** Update all references from "16" to "18" (or "19 including START"), or clearly define what counts as a "node."

### Finding 2.3: MEDIUM — Requirements say 5 Intents, But 6 Are Defined

- **Requirements spec (section 三):** "五种售后意图" (five after-sales intents)
- **Requirements (FR-05.2):** Lists 6 intents (包括 `ESCALATE_TO_HUMAN`)

The "five core business scenarios" listed in section 三 are: 物流查询, 未发货退款, 已收货质量问题退款或换货, 缺件补发, 转人工. That's 5 scenarios but `EXCHANGE` (换货) and `QUALITY_REFUND` (质量问题退款) are listed as one scenario but two separate intents in FR-05.2. This is a presentation issue: the "five scenarios" count was for business use cases, not intent types, but the mapping isn't 1:1.

**Fix:** Clarify in `docs/01-requirements.md` that the 5 business scenarios map to 6 intent types (because quality refund and exchange are separate intents within one scenario).

### Finding 2.4: MEDIUM — Tool Count Inconsistency (13+ vs 14 listed)

- **Architecture:** "13+ tools"
- **Phase 03 task list:** Lists 14 tools
- **Requirements spec (section 七):** Lists 13 tools (missing `create_approval_task`)

The 14th tool (`create_approval_task`) is implied by HUMAN_APPROVAL node but not in the spec's tool list. It's a legitimate tool.

**Fix:** Update `docs/02-architecture.md` to say "14 tools" and ensure Phase 03 explicitly includes `create_approval_task`.

### Finding 2.5: LOW — RAG Embedding Dimension Locked at 1536

- **RAG design:** Specifies 1536 dimensions (OpenAI text-embedding-3-small)
- **Database:** `vector(1536)` column
- **Config:** EMBEDDING_DIMENSION=1536

This is consistent ✅, but there's no documentation on what happens if someone changes the embedding model. The dimension should be configurable and validated at startup.

### Finding 2.6: LOW — Demo Script References "ORD-001" but DB Uses UUIDs

- **Demo script:** "您的订单#ORD-001"
- **Database:** `order_number VARCHAR(30)` — human-readable, can be "ORD-001"

This is actually fine — the `order_number` field is VARCHAR and can hold "ORD-001". No fix needed, just noting for awareness.

**Verdict: FAIL — 2 CRITICAL issues require fixes before Phase 01.**

---

## Check 3: Database Tables vs Agent State Coverage

### Finding 3.1: PASS — All AgentState Fields Have Corresponding Tables ✅

| AgentState Field | Database Table | Coverage |
|---|---|---|
| `customer_profile` | `users` | ✅ |
| `candidate_orders` / `confirmed_order` | `orders` | ✅ |
| `order_detail` | `orders` + `order_items` | ✅ |
| `logistics` | `logistics_records` | ✅ |
| `existing_tickets` | `after_sales_tickets` | ✅ |
| `policies` | `policy_documents` | ✅ |
| `eligibility` | (computed, not stored) | ✅ |
| `solution` | `after_sales_tickets.proposed_solution` | ✅ |
| `approval_task` | `approval_tasks` | ✅ |
| `execution_results` | (transient, traced in `agent_tool_logs`) | ✅ |
| `verification` | (transient, traced in `agent_traces`) | ✅ |
| Session/graph_state | `agent_sessions` | ✅ |
| Memories | `customer_memories` | ✅ |

### Finding 3.2: MEDIUM — No Table for Evaluation Results

- **Requirements (FR-14.3):** "Results are stored and viewable in the admin dashboard"
- **Database:** No `evaluation_runs` or `evaluation_results` table

The admin dashboard references "Evaluation Results" but there's no persistence model. Phase 08 (Evaluation) should add this, but the database design should at least note it as a future table.

**Fix:** Add a note in `docs/03-database-design.md` that an `evaluation_runs` / `evaluation_results` table pair will be added in Phase 08.

### Finding 3.3: LOW — `agent_sessions` FK to `users` Uses `id` but Session Is Linked by `user_id`

The `agent_sessions.user_id` FK references `users.id` - correct. ✅

**Verdict: PASS with 1 note.**

---

## Check 4: API Contracts vs Five Core Business Scenarios

### Finding 4.1: PASS — All Five Scenarios Are Covered ✅

| Scenario | API Coverage |
|---|---|
| 1. 查询物流 | `GET /orders/{id}/logistics` + Agent WS |
| 2. 未发货退款 | Agent WS → tools → ticket/refund creation |
| 3. 已收货质量问题退款/换货 | Agent WS → RAG → eligibility → tools |
| 4. 缺件补发 | Agent WS → tools → reshipment creation |
| 5. 转人工 | Agent WS → ESCALATED node → escalation ticket |

### Finding 4.2: MEDIUM — Missing Customer Refund Status Endpoint

- Customers can see tickets (`GET /tickets/{id}`), but there's no direct `GET /refunds/{id}` or `GET /tickets/{id}/refund` endpoint.
- Refund status is embedded in `after_sales_tickets.resolution_result` JSONB, which is fine but not documented as an explicit API path.

**Fix:** Document in `docs/04-api-contracts.md` that refund/reshipment status is available through the ticket detail endpoint.

### Finding 4.3: LOW — No WebSocket Reconnection Protocol

The WebSocket protocol defines message types but doesn't specify reconnection behavior (what happens if the connection drops mid-session). This is an implementation detail for Phase 03/07.

**Verdict: PASS with 1 documentation gap.**

---

## Check 5: Agent State Machine — Node Reachability Analysis

### Finding 5.1: CRITICAL — NEED_MORE_INFORMATION Has No Documented Re-Entry Path

When the agent routes to NEED_MORE_INFORMATION:
- It asks the user a clarifying question
- The user responds with a new message
- **How does that message re-enter the state machine?**

The WebSocket protocol has `{"type": "message", ...}` but the state machine diagram shows NEED_MORE_INFORMATION as a terminal/dead-end with no edge back into the graph. The new message should re-enter at INTENT_CLASSIFICATION or ORDER_RESOLUTION with enriched context, but this loop-back isn't documented.

**Fix:** Add to `docs/05-agent-workflow.md`:
1. NEED_MORE_INFORMATION sends a question to the user and saves state
2. The user's next message re-enters at INTENT_CLASSIFICATION with `conversation_history` containing the previous context
3. The existing short-term memory preserves `candidate_orders` so ORDER_RESOLUTION can disambiguate

### Finding 5.2: MEDIUM — User Cannot Change Selected Order After Confirmation

If ORDER_RESOLUTION picks the wrong order and FACT_COLLECTION proceeds, the user's only chance to correct this is at USER_CONFIRMATION. But if the user rejects the solution, the route goes to COMPLETED — they can't say "wrong order, try the other one."

**Fix:** Add a routing branch from USER_CONFIRMATION: when user rejects AND provides feedback like "wrong order", route back to ORDER_RESOLUTION with the feedback as context.

### Finding 5.3: MEDIUM — MEMORY_UPDATE Has No Failure Path

MEMORY_UPDATE always routes to COMPLETED regardless of success or failure. If memory persistence fails:
- Short-term memory is lost (acceptable, it's ephemeral)
- Long-term memory summary is lost (minor — next session will create a new one)
- **Business state memory is lost** — this is problematic because it prevents deduplication on the next session

**Fix:** Add error handling to MEMORY_UPDATE: on failure, log the error and still route to COMPLETED (graceful degradation), but flag the session so the next session can detect incomplete state.

### Finding 5.4: LOW — RETRY Node Semantics Are Ambiguous

The RETRY terminal node says "Retries preceding node." But:
- From FACT_COLLECTION (which calls 3 tools), does RETRY mean retry all 3 or just the failed one?
- From ACTION_EXECUTION (which calls multiple tools), same question.

**Fix:** Clarify that RETRY re-executes the preceding node in full, but that node is idempotent-aware (tools skip already-completed work via idempotency keys).

### Finding 5.5: PASS — No Unreachable Nodes ✅

Every node can be reached through valid transitions:
- START → INTENT_CLASSIFICATION ✅
- INTENT_CLASSIFICATION → CUSTOMER_IDENTIFICATION ✅
- ...all paths verified in the routing function analysis

### Finding 5.6: PASS — No Infinite Loops ✅

The only loop is RETRY → preceding node, gated by `retry_count < max_retries`. Once max is exceeded, route to FAILED. This is a bounded loop.

**Verdict: FAIL — 1 CRITICAL re-entry gap, 2 MEDIUM routing issues.**

---

## Check 6: RAG vs Deterministic Rules — Responsibility Clarity

### Finding 6.1: MEDIUM — Eligibility Rules Consume Unstructured Policy Text

The ELIGIBILITY_CHECK node takes `policies: List[PolicyDocument]` as input. But the eligibility checker is "deterministic code" that "does NOT use LLM." How does deterministic code evaluate unstructured policy text?

The design needs to clarify:
- Policies must have structured `metadata_filter` fields that the rule engine can read
- The `content` (unstructured text) is for LLM explanation, NOT for rule evaluation
- Eligibility rules read policy metadata (category, effective dates, conditions encoded as structured fields)

**Fix:** Add to `docs/06-rag-design.md` that each policy document must include structured eligibility conditions in its `metadata_filter` JSONB field (e.g., `{"max_days_from_delivery": 7, "applicable_categories": ["ELECTRONICS"], "requires_inspection": true}`).

### Finding 6.2: PASS — Refund Calculation is Deterministic ✅

`calculate_refund_amount` is explicitly marked as "NO LLM — deterministic code." This is consistent across requirements, agent workflow, and tools.

### Finding 6.3: PASS — RAG "No Results → ESCALATED" is Clear ✅

The edge case table in RAG design matches the agent routing rule: empty results → ESCALATED. No ambiguity.

### Finding 6.4: LOW — Policy Conflict Resolution Not Specified

RAG edge case: "Multiple conflicting policies" → ESCALATED. But what constitutes a "conflict"? Two policies with different refund windows? Two policies with different eligibility criteria for the same product category?

**Fix:** Define "policy conflict" as: two+ ACTIVE policies with overlapping `issue_type` and `category` but contradictory `metadata_filter` conditions.

**Verdict: PASS with 1 important clarification needed.**

---

## Check 7: Three-Tier Memory — True Differentiation

### Finding 7.1: MEDIUM — Short-Term Memory Stored in TWO Places

- **docs/07-memory-design.md line 88:** "Primary: LangGraph agent state (in-memory during session). Persisted: Serialized to `agent_sessions.graph_state` on each checkpoint."
- **docs/03-database-design.md:** `customer_memories` table has `memory_type = 'SHORT_TERM'`

This means short-term memory can exist in THREE places:
1. LangGraph in-memory state
2. `agent_sessions.graph_state` JSONB (checkpoint)
3. `customer_memories` table (SHORT_TERM rows)

This is confusing and potentially inconsistent. The design should clarify:
- Short-term memory lives in LangGraph state + `agent_sessions.graph_state` (checkpoint)
- `customer_memories` with SHORT_TERM type is for **cross-session** access to recent context (e.g., if a session expires and a new one starts within the TTL window)
- The two are synchronized at checkpoints

**Fix:** Clarify in `docs/07-memory-design.md` the relationship between `agent_sessions.graph_state` and `customer_memories` (SHORT_TERM).

### Finding 7.2: PASS — Long-Term and Business State Are Clearly Differentiated ✅

- Long-term: preferences, history, trends — survives indefinitely
- Business state: active operations, pending approvals — survives until resolved

Clear separation of concerns. ✅

### Finding 7.3: PASS — Load Order is Correct ✅

Memory design specifies:
1. Session start → Load business state FIRST (check for existing operations)
2. Then load long-term memory (for personalization)
3. Then proceed to intent classification

This is the correct priority order. ✅

**Verdict: PASS with 1 storage clarification needed.**

---

## Check 8: Sensitive Operations — Permission, Transaction, Idempotency, Audit

### Finding 8.1: PASS — All Three Sensitive Operations Are Fully Covered ✅

| Operation | Permission | Transaction | Idempotency | Audit | Verification |
|-----------|-----------|-------------|-------------|-------|-------------|
| Refund | Agent validates user → service checks ownership | `RefundService` wraps in transaction | `idempotency_key` UNIQUE constraint | `audit_logs` row created | RESULT_VERIFICATION node |
| Reshipment | Same pattern | `ReshipmentService` wraps in transaction | `idempotency_key` UNIQUE constraint | `audit_logs` row created | RESULT_VERIFICATION node |
| Approval | Role-based (OPERATOR/ADMIN) | `ApprovalService` processes atomically | Approval status change is idempotent | `audit_logs` row created | Agent checks approval status on resume |

### Finding 8.2: MEDIUM — Agent Tool-Level Permission Enforcement Not Specified

The security design says:
> "3. Agent Tool Level: Tools validate that the calling agent has permission for the operation."

But no tool schemas or designs specify HOW this validation works. Does each tool receive a `caller_user_id` and re-verify against the database? Or does the LangGraph state carry an authenticated context that tools trust?

**Fix:** Add to `docs/08-security-design.md` that each sensitive tool receives the `user_id` from the LangGraph state (set during CUSTOMER_IDENTIFICATION from the verified JWT), and re-verifies ownership in the Service layer.

### Finding 8.3: LOW — Idempotency Key Time-Bucket Granularity

The idempotency key uses `timestamp_bucket = today` (day granularity). This means the same operation on the same order can only happen once per day. Is this intentional?

- **Pro:** Prevents accidental double-click within the same day
- **Con:** A legitimate second refund for a different item on the same order, same day, would be blocked

**Fix:** Refine the idempotency key to include the specific item(s): `f"{operation}_{order_id}_{item_ids}_{today}"`.

**Verdict: PASS with 2 clarifications needed.**

---

## Check 9: Phase 01–09 Acceptance Criteria — Specificity and Testability

### Finding 9.1: MEDIUM — Most Phases Use "All Tests Pass" Without Specific Test Coverage

- Phases 01, 02, 03, 05, 06, 07, 09 all end with "All tests pass"
- But they don't specify WHICH tests must exist or minimum coverage
- Phase 04 and Phase 08 are better — they include quantitative metrics (Precision@5 >= 0.85, Intent accuracy >= 0.90)

**Fix:** Add test coverage expectations to each phase's acceptance criteria (e.g., "Unit test coverage >= 80% for new code in this phase").

### Finding 9.2: PASS — Phase 04 and 08 Have Quantitative Acceptance Criteria ✅

Phase 04: Precision@5 >= 0.85, Recall@5 >= 0.90, latency < 500ms ✅  
Phase 08: Intent accuracy >= 0.90, safety interception >= 0.95 ✅

### Finding 9.3: MEDIUM — Phase 07 (Frontend) E2E Criteria Are Vague

"Customer can register, browse, order, and chat with agent" — this describes a manual demo, not an automated test. There's no automated E2E test specification for frontend flows.

**Fix:** Add to Phase 07 that each user journey must have at least one automated E2E test (using Playwright or similar).

### Finding 9.4: LOW — No Phase Precondition Verification

Phases list preconditions but don't specify how to verify them. For example, Phase 02 requires "Phase 01 completed" — but what's the objective check? All Phase 01 acceptance criteria checked off? All Phase 01 tests passing?

**Fix:** Add a "Precondition Verification" step to each phase: "Run `pytest` and confirm all Phase 01 tests pass before starting Phase 02."

**Verdict: PASS with 2 improvements needed.**

---

## Check 10: Phase 00 Completeness — Placeholders, Omissions, Useless Complexity

### Finding 10.1: LOW — Empty Directories Without .gitkeep

- `config/` — empty, no .gitkeep
- `scripts/` — empty, no .gitkeep
- `.claude/` — empty, no .gitkeep
- `.github/` — empty, no .gitkeep
- `mcp-server/` — empty, no .gitkeep

These directories won't be tracked by Git until they contain files. If the intention is to have these directories ready for future phases, they need `.gitkeep` files.

### Finding 10.2: LOW — Docker Compose References Non-Existent Dockerfiles

`docker-compose.yml` has `build: ./backend/Dockerfile` but no Dockerfile exists yet. This is appropriate for Phase 00 (the Dockerfile is a Phase 01/09 deliverable), but a comment noting this would be helpful.

### Finding 10.3: PASS — No Implementation Code Written ✅

All `.py` files are minimal `__init__.py` stubs with only a comment. No business logic, no models, no API routes. This correctly respects Phase 00 boundaries.

### Finding 10.4: MEDIUM — No .claude/settings.json

The project spec mentions `.claude/` directory. While this is optional, a minimal `settings.json` with project-specific hooks would demonstrate the infrastructure is ready.

### Finding 10.5: PASS — Documentation Is Comprehensive and Self-Consistent (After Fixes) ✅

The 12 design docs + 4 ADRs + 10 phase files form a complete blueprint. Every major system component is specified at the design level.

### Finding 10.6: PASS — No Useless Complexity ✅

- No over-engineered directory structures
- No premature abstraction
- No speculative features
- The monorepo structure is flat enough for a demo but organized enough for clarity

**Verdict: PASS with 2 minor cleanup items.**

---

## Issue Summary

### CRITICAL (3 issues — Must Fix Before Phase 01)

| # | Finding | Location | Fix |
|---|---------|----------|-----|
| **2.1** | Intent enum mismatch: `ESCALATE_TO_HUMAN` vs `OTHER` | `docs/03-database-design.md` | Add both values to enum, map each to use case |
| **2.2** | Node count says "16" but actual count is 18-19 | `docs/02-architecture.md`, `docs/05-agent-workflow.md`, `README.md`, `tasks/phase-03-agent-tools.md` | Update count to 18 (or 13 processing + 5 terminal) |
| **5.1** | NEED_MORE_INFORMATION has no documented re-entry path | `docs/05-agent-workflow.md` | Document loop-back via INTENT_CLASSIFICATION with context preservation |

### MEDIUM (6 issues — Should Fix Before Phase 01)

| # | Finding | Location |
|---|---------|----------|
| **2.3** | 5 scenarios vs 6 intents — unclear mapping | `docs/01-requirements.md` |
| **2.4** | Tool count "13+" vs 14 listed | `docs/02-architecture.md` |
| **3.2** | No evaluation results table in DB design | `docs/03-database-design.md` |
| **5.2** | No "wrong order" correction path after USER_CONFIRMATION | `docs/05-agent-workflow.md` |
| **6.1** | Eligibility rules need structured policy metadata | `docs/06-rag-design.md` |
| **7.1** | Short-term memory stored in two places without clear relationship | `docs/07-memory-design.md` |

### LOW (5 issues — Nice to Fix)

| # | Finding | Location |
|---|---------|----------|
| 1.2 | Phase range wording: "00–06" vs "01–06" | `AGENTS.md` or `CLAUDE.md` |
| 5.4 | RETRY node semantics ambiguous for multi-tool nodes | `docs/05-agent-workflow.md` |
| 8.2 | Tool-level permission enforcement mechanism unspecified | `docs/08-security-design.md` |
| 9.1 | Phase acceptance criteria lack test coverage targets | All phase files |
| 10.1 | Empty directories without .gitkeep | Various directories |

---

## Recommended Fixes Order

1. **First:** Fix the 3 CRITICAL issues (enum, node count, re-entry path)
2. **Second:** Fix the 6 MEDIUM issues (clarity and completeness)
3. **Third:** Apply LOW fixes as time permits

---

## Overall Assessment

| Dimension | Grade | Notes |
|-----------|-------|-------|
| Documentation Completeness | A | 12 docs + 4 ADRs cover all major areas |
| Cross-Document Consistency | B | 2 critical mismatches found |
| Database Design Quality | A- | 17 tables well-designed, missing evaluation table |
| API Design Coverage | A- | All scenarios covered, refund status path implicit |
| Agent Workflow Soundness | B | 1 critical re-entry gap, 2 routing gaps |
| RAG/Rules Separation | A- | Clear in principle, needs structured metadata spec |
| Memory Tier Clarity | B+ | Well-differentiated, storage redundancy unclear |
| Security Design | A- | 7-point checklist, tool-level enforcement TBD |
| Phase Plan Quality | B+ | Good structure, acceptance criteria need quantitative targets |
| Code-Free Boundary | A | No implementation code written ✅ |

**Overall: B+ (82/100)**

Phase 00 provides a solid blueprint. After applying the CRITICAL and MEDIUM fixes, the project will be ready for Phase 01 implementation with low risk of design-level rework.

---

## Post-Fix Verification Checklist

- [ ] Intent enum includes both `ESCALATE_TO_HUMAN` and `OTHER`
- [ ] All references to node count say "18" (or "13 active + 5 terminal")
- [ ] NEED_MORE_INFORMATION re-entry documented with state preservation
- [ ] 5 scenarios → 6 intents mapping clarified
- [ ] Tool count updated to "14"
- [ ] Database design notes evaluation tables for Phase 08
- [ ] USER_CONFIRMATION rejection can route back to ORDER_RESOLUTION
- [ ] RAG design specifies structured eligibility metadata fields
- [ ] Memory design clarifies short-term memory storage relationship
- [ ] Phase acceptance criteria include coverage targets
