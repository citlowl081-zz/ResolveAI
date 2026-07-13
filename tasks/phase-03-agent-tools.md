# Phase 03 — Agent Tools

## Phase Goals

Implement the 13+ agent tools with unified return format, logging, retry logic, and Pydantic schemas. Build the LangGraph state machine with all 18 nodes (13 active + 5 terminal) and routing logic. Integrate the LLM client for NLU tasks.

## Preconditions

- Phase 02 completed (business backend with services and APIs).
- LLM API key configured.

## Task Checklist

### 3.1 LLM Client
- [ ] `llm/client.py` — Abstract LLM client interface.
- [ ] `llm/anthropic_client.py` — Anthropic Claude implementation.
- [ ] `llm/structured_output.py` — Pydantic model → tool use schema, parse + retry.
- [ ] `llm/mock_client.py` — Mock client for testing.

### 3.2 Tool Definitions (13+ Tools)
- [ ] `tools/get_customer_profile.py`
- [ ] `tools/list_customer_orders.py`
- [ ] `tools/get_order_detail.py`
- [ ] `tools/get_logistics_status.py`
- [ ] `tools/get_existing_after_sales_ticket.py`
- [ ] `tools/search_after_sales_policy.py`
- [ ] `tools/check_after_sales_eligibility.py`
- [ ] `tools/calculate_refund_amount.py`
- [ ] `tools/create_after_sales_ticket.py`
- [ ] `tools/create_refund_request.py`
- [ ] `tools/create_reshipment_order.py`
- [ ] `tools/update_ticket_status.py`
- [ ] `tools/send_customer_notification.py`
- [ ] `tools/escalate_to_human.py`

### 3.3 Tool Framework
- [ ] `tools/base.py` — Base tool class with unified return format.
- [ ] `tools/registry.py` — Tool registry for lookup and invocation.
- [ ] `tools/executor.py` — Execute with retry, logging, error handling.
- [ ] `tools/schemas.py` — Common Pydantic schemas for tool I/O.

### 3.4 LangGraph State Machine
- [ ] `agent/state.py` — AgentState TypedDict definition.
- [ ] `agent/graph.py` — Graph construction with all 16 nodes and edges.
- [ ] `agent/nodes/intent_classification.py`
- [ ] `agent/nodes/customer_identification.py`
- [ ] `agent/nodes/order_resolution.py`
- [ ] `agent/nodes/fact_collection.py`
- [ ] `agent/nodes/policy_retrieval.py`
- [ ] `agent/nodes/eligibility_check.py`
- [ ] `agent/nodes/solution_generation.py`
- [ ] `agent/nodes/user_confirmation.py`
- [ ] `agent/nodes/risk_check.py`
- [ ] `agent/nodes/human_approval.py`
- [ ] `agent/nodes/action_execution.py`
- [ ] `agent/nodes/result_verification.py`
- [ ] `agent/nodes/memory_update.py`
- [ ] `agent/routing.py` — All routing functions.

### 3.5 Agent Session Management
- [ ] `agent/session.py` — Create, load, save, expire sessions.
- [ ] `agent/resume.py` — Resume from checkpoint.
- [ ] `agent/api.py` — HTTP and WebSocket endpoints for agent interaction.

### 3.6 Integration with Services
- [ ] All tools call Service layer (not DB directly).
- [ ] Tool execution logs written to agent_tool_logs table.
- [ ] Agent traces written to agent_traces table.
- [ ] Session state persisted after each node.

### 3.7 Testing
- [ ] Individual tool tests (with mocked services).
- [ ] Tool executor tests (retry, error handling).
- [ ] Node tests (each node in isolation).
- [ ] Routing tests (each edge condition).
- [ ] Workflow tests (full graph with mocked LLM).
- [ ] Session resume tests.

## Acceptance Criteria

- [ ] All 14 tools have Pydantic schemas, unified return format, and tests.
- [ ] State machine executes end-to-end with mocked LLM.
- [ ] Each node correctly routes to the expected next node.
- [ ] Tool failures trigger retry (max 2) then route to FAILED.
- [ ] LLM structured output failures retry once then route to FAILED.
- [ ] Session state is serializable and restorable.
- [ ] All tests pass (unit + integration + agent).
- [ ] Ruff, mypy, pytest all pass.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
