# Phase 08 — Evaluation Framework

## Phase Goals

Build the agent evaluation framework with 50+ test cases, automated scoring, and a results dashboard. This is critical for demonstrating the agent's capabilities in an interview setting.

## Preconditions

- Phase 03–06 completed (full agent workflow).
- All tool implementations complete.
- Test infrastructure in place.

## Task Checklist

### 8.1 Evaluation Data
- [ ] Create `data/evaluation/cases.json` — 50+ evaluation cases.
- [ ] Each case: user_message, expected_intent, expected_tool_calls, expected_outcome, context (user_id, order_id, etc.).
- [ ] Categories: normal flows, edge cases, safety, resume/recovery, complex.

### 8.2 Evaluation Runner
- [ ] `tests/e2e/conftest.py` — Evaluation fixtures.
- [ ] `tests/e2e/test_evaluation.py` — Main evaluation runner.
- [ ] Run each case against the agent with mocked LLM.
- [ ] Compare agent output against expected values.
- [ ] Record results per case and aggregate metrics.

### 8.3 Metrics Calculation
- [ ] Intent classification accuracy.
- [ ] Tool selection accuracy (which tools were called).
- [ ] Tool parameter correctness (were arguments correct).
- [ ] RAG policy hit rate (was relevant policy retrieved).
- [ ] Task completion rate (did agent reach COMPLETED).
- [ ] Safety interception rate (were unsafe ops blocked).
- [ ] Approval trigger accuracy (were high-risk ops escalated).
- [ ] Auto-resolution rate (no human intervention needed).
- [ ] Average tool calls per task.
- [ ] Average response time.

### 8.4 Results Storage
- [ ] Store results in database (evaluation_runs table if needed).
- [ ] Per-case results with pass/fail and detailed reasons.
- [ ] Aggregate metrics with trends across runs.

### 8.5 Admin Dashboard
- [ ] Trigger evaluation run from admin UI.
- [ ] View per-case results.
- [ ] View aggregate metrics with charts.
- [ ] Compare runs (if multiple).

### 8.6 Testing
- [ ] Test that evaluation runner correctly scores known outcomes.
- [ ] Test that mocked LLM returns expected structured outputs.
- [ ] Verify no false positives (passing when should fail).
- [ ] Verify no false negatives (failing when should pass).

## Acceptance Criteria

- [ ] 50+ evaluation cases defined.
- [ ] Evaluation runner executes all cases.
- [ ] All metrics calculated correctly.
- [ ] Results viewable in admin dashboard.
- [ ] Intent accuracy >= 0.90 on evaluation set.
- [ ] Safety interception rate >= 0.95.
- [ ] No fabricated evaluation data.
- [ ] All tests pass.

## Completion Record

- **Started:** 2026-07-15
- **Completed:** 2026-07-15
