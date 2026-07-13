# 09 — Testing Strategy

## Testing Philosophy

1. **Tests are part of the deliverable.** Untested code is incomplete code.
2. **Every layer is tested independently.**
3. **LLM calls are always mocked in tests.**
4. **Database tests use a real PostgreSQL instance (test database).**
5. **50+ evaluation cases are run against the full system.**

## Test Pyramid

```
         ┌──────┐
         │ E2E  │  10 cases (critical user journeys)
         ├──────┤
         │ Agent│  20 cases (workflow tests with mocked LLM)
         ├──────┤
         │ Int. │  30+ cases (API + DB integration)
         ├──────┤
         │ Unit │  80+ cases (functions, services, rules, repositories)
         └──────┘
```

## Test Categories

### 1. Unit Tests

**Location:** `backend/tests/unit/`

| Test File | What It Tests |
|-----------|---------------|
| `test_rules.py` | Rule engine: eligibility logic, risk assessment, refund calculation, state transitions |
| `test_repositories.py` | Repository methods with mocked DB session |
| `test_schemas.py` | Pydantic validation: valid/invalid inputs, edge cases |
| `test_security.py` | Input sanitization, PII masking, permission checks, Prompt injection detection |
| `test_tool_schemas.py` | Tool input/output schemas |

**Rules:**
- Fast (no DB, no network).
- Mock all external dependencies.
- Test both happy path and error cases.

### 2. Repository Tests

**Location:** `backend/tests/integration/test_repositories.py`

- Test against a real test database.
- Each test creates its own data and cleans up.
- Verify SQL queries work correctly.

### 3. Service Tests

**Location:** `backend/tests/integration/test_services.py`

- Test business logic with real repositories.
- Verify transaction boundaries.
- Test state transition validation.
- Test idempotency behavior.

### 4. API Integration Tests

**Location:** `backend/tests/integration/test_api/`

| Test File | What It Tests |
|-----------|---------------|
| `test_auth.py` | Register, login, refresh, me |
| `test_products.py` | List, detail |
| `test_orders.py` | Create, list, detail, logistics |
| `test_tickets.py` | List, detail, update (admin) |
| `test_admin.py` | Dashboard, approvals, traces, logs |

**Tools:** `httpx.AsyncClient` with FastAPI `TestClient`.

### 5. Agent Tests

**Location:** `backend/tests/agent/`

| Test File | What It Tests |
|-----------|---------------|
| `test_nodes.py` | Each LangGraph node in isolation with mocked dependencies |
| `test_workflows.py` | Full state machine execution with mocked LLM |
| `test_tools.py` | Individual tool execution with real services |
| `test_routing.py` | Routing logic: each edge condition |
| `test_checkpointing.py` | State save/restore, session resume |

**LLM Mocking:**
```python
@pytest.fixture
def mock_llm():
    with patch("app.llm.client.ChatLLM.generate") as mock:
        # Return predefined structured outputs
        mock.side_effect = load_mock_responses("fixtures/llm_responses/")
        yield mock
```

### 6. RAG Tests

**Location:** `backend/tests/rag/`

| Test | What It Tests |
|------|---------------|
| `test_retrieval.py` | Vector search accuracy |
| `test_ingestion.py` | Document chunking, embedding, storage |
| `test_filtering.py` | Metadata filtering, status filtering |
| `test_edge_cases.py` | No results, conflicting policies, expired policies |

**Evaluation:**
- Precision@5: Target > 0.85
- Recall@5: Target > 0.90
- MRR: Target > 0.80

### 7. Security Tests

**Location:** `backend/tests/security/`

| Test | What It Tests |
|------|---------------|
| `test_permissions.py` | Each role can only access allowed endpoints |
| `test_idempotency.py` | Duplicate requests don't create duplicate resources |
| `test_injection.py` | Prompt injection patterns are caught |
| `test_pii_masking.py` | Sensitive data masked in logs |
| `test_state_transitions.py` | Illegal status changes rejected |

### 8. End-to-End Tests

**Location:** `backend/tests/e2e/`

Critical user journeys:
1. Register → Browse → Order → Check logistics → Query agent → Get response
2. Pre-ship refund: Order → Agent request → Confirmation → Refund created → DB verified
3. Post-delivery quality refund: Order (delivered) → Agent → Policy check → Approval (if high amount) → Refund
4. Missing parts reshipment: Order → Agent → Reshipment created
5. Cross-session resume: Create ticket → New session → Query progress → No duplicate
6. Human escalation: Order → Agent → Not eligible → Escalation ticket created

## Evaluation Cases (50+ Cases)

**Location:** `data/evaluation/cases.json`

### Intent Classification Cases (10)
1. Normal logistics inquiry
2. Pre-ship refund request
3. Post-delivery quality complaint
4. Exchange request
5. Missing parts report
6. Human escalation request
7. Ambiguous: unclear which order
8. Multiple issues in one message
9. Greeting / non-after-sales message
10. Off-topic / chitchat

### Normal Flow Cases (8)
11. Logistics inquiry — standard
12. Pre-ship refund — single item
13. Pre-ship refund — multiple items, partial
14. Post-delivery quality refund — within 7 days
15. Post-delivery exchange — clothing
16. Missing parts — single item
17. Missing parts — multiple items
18. Human escalation — complex issue

### Edge Case Cases (12)
19. Order not found
20. Multiple candidate orders (ambiguous)
21. Already has active ticket
22. Already refunded
23. Already reshipped
24. Over refund window
25. Non-returnable product (food)
26. Policy not found (RAG returns empty)
27. Policy conflict
28. High-risk user
29. High-amount refund (> threshold)
30. Coupon-applied order

### Safety Cases (8)
31. Prompt injection attempt #1
32. Prompt injection attempt #2
33. Customer trying to view other's order
34. LLM output fails structured validation
35. Tool execution fails (DB error)
36. Tool execution timeout
37. Duplicate refund prevention
38. Duplicate reshipment prevention

### Resume & Recovery Cases (6)
39. Session interrupted before confirmation
40. Session interrupted during human approval
41. Cross-session business state query
42. Agent recovers from LLM error
43. Agent recovers from tool failure (retry success)
44. Agent handles retry exhaustion

### Complex Cases (6+)
45. Return shipping guidance
46. Partial refund for multi-item order
47. Refund with coupon adjustment
48. Price difference refund
49. Exchange with stock check
50. Multiple tickets, same order, different items

## Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Intent Classification Accuracy | >= 0.90 | % of correctly classified intents |
| Tool Selection Accuracy | >= 0.90 | % of correct tool choices |
| Tool Parameter Correctness | >= 0.85 | % of correct tool arguments |
| Policy Hit Rate (RAG) | >= 0.85 | % of cases where relevant policy found in top-5 |
| Task Completion Rate | >= 0.80 | % of cases reaching COMPLETED successfully |
| Safety Interception Rate | >= 0.95 | % of unsafe operations prevented |
| Approval Trigger Accuracy | >= 0.90 | % of high-risk cases correctly escalated |
| Auto-Resolution Rate | >= 0.70 | % of cases resolved without human intervention |
| Avg Tool Calls Per Task | <= 6 | Mean number of tool calls per completed task |

## Running Tests

```bash
# All tests
cd backend && pytest -v

# With coverage
cd backend && pytest -v --cov=app --cov-report=term-missing

# Specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/agent/ -v
pytest tests/rag/ -v
pytest tests/security/ -v

# Evaluation suite
pytest tests/e2e/test_evaluation.py -v --eval-cases=all

# Single evaluation case
pytest tests/e2e/test_evaluation.py -v --eval-case=1
```

## CI Pipeline (Future)

```
Lint (Ruff) → Type Check (mypy) → Unit Tests → Integration Tests → Agent Tests → RAG Tests → Security Tests → Build
```

## Prohibited Testing Anti-Patterns

- ❌ Deleting failing tests to make CI pass.
- ❌ Fabricating test results.
- ❌ Tests that depend on execution order.
- ❌ Tests that call real LLM APIs.
- ❌ Tests without assertions.
- ❌ Commenting out assertions to "pass".
