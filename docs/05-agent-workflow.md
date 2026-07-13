# 05 — Agent Workflow Design

## State Machine Overview

The ResolveAI agent uses a LangGraph state machine with 16 explicit nodes. Each node has a clear responsibility and deterministic routing logic.

```
                          ┌─────────────┐
                          │    START    │
                          └──────┬──────┘
                                 │
                    ┌────────────▼────────────┐
                    │  INTENT_CLASSIFICATION   │
                    │  (LLM)                   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ CUSTOMER_IDENTIFICATION  │
                    │ (Tool: get_profile)      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   ORDER_RESOLUTION       │
                    │ (Tool: list_orders)      │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────────┐
                    │ ORDER   │  │ NEED_MORE     │
                    │ FOUND   │  │ INFORMATION   │
                    └──────┬──┘  └───┬──────────┘
                           │          │ (loop back
                           │          │  to user)
                    ┌──────▼──────────▼────────┐
                    │    FACT_COLLECTION        │
                    │ (Tools: get_detail,      │
                    │  get_logistics,          │
                    │  get_existing_tickets)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   POLICY_RETRIEVAL       │
                    │ (RAG: search_policies)   │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────┐
                    │ POLICIES│  │ NO       │
                    │ FOUND   │  │ POLICIES │
                    └──────┬──┘  └───┬──────┘
                           │          │→ ESCALATED
                    ┌──────▼──────────▼────────┐
                    │   ELIGIBILITY_CHECK       │
                    │ (Rules Engine + Code)     │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────┐
                    │ ELIGIBLE│  │ NOT      │
                    └──────┬──┘  │ ELIGIBLE │
                           │     └───┬──────┘
                           │         │→ COMPLETED
                    ┌──────▼──────────▼────────┐
                    │  SOLUTION_GENERATION      │
                    │ (LLM plan + Code calc)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  USER_CONFIRMATION       │
                    │ (Wait for user input)    │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────┐
                    │ CONFIRMED│ │ REJECTED │
                    └──────┬──┘  └───┬──────┘
                           │         │→ COMPLETED
                    ┌──────▼──────────▼────────┐
                    │     RISK_CHECK            │
                    │ (Rules Engine)            │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────┐
                    │ LOW RISK│  │ HIGH RISK│
                    └──────┬──┘  └───┬──────┘
                           │          │
                           │  ┌───────▼─────────┐
                           │  │ HUMAN_APPROVAL   │
                           │  │ (Pause & Wait)   │
                           │  └───────┬─────┬────┘
                           │          │     │
                           │   ┌──────▼──┐ ┌▼──────┐
                           │   │APPROVED │ │REJECTED│
                           │   └──────┬──┘ └───┬───┘
                           │          │        │→ COMPLETED
                    ┌──────▼──────────▼────────┐
                    │   ACTION_EXECUTION        │
                    │ (Tools: create_ticket,    │
                    │  create_refund, etc.)     │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────┐
                    │ SUCCESS │  │ FAILED   │
                    └──────┬──┘  └───┬──────┘
                           │         │→ RETRY or FAILED
                    ┌──────▼──────────▼────────┐
                    │  RESULT_VERIFICATION      │
                    │ (Check DB state)          │
                    └──────┬──────────┬────────┘
                           │          │
                    ┌──────▼──┐  ┌───▼──────┐
                    │ VERIFIED│  │ MISMATCH │
                    └──────┬──┘  └───┬──────┘
                           │         │→ RETRY or FAILED
                    ┌──────▼──────────▼────────┐
                    │   MEMORY_UPDATE           │
                    │ (Save all memory tiers)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      COMPLETED           │
                    └─────────────────────────┘
```

## Node Specifications

### 1. INTENT_CLASSIFICATION

| Field | Value |
|-------|-------|
| **Node** | `intent_classification` |
| **Responsibility** | Classify user message into one of 6 intent types |
| **Input** | `user_message: str`, `conversation_history: List[Message]` |
| **Output** | `intent: IntentType`, `confidence: float`, `extracted_entities: dict` |
| **LLM Call** | Yes — structured output to IntentClassification schema |
| **Max Retries** | 1 (retry with re-prompt on parse failure) |
| **Routes To** | CUSTOMER_IDENTIFICATION |
| **Error Route** | FAILED (if intent uncertain → ask clarifying question) |
| **Interruptible** | No |
| **Resumable** | Yes (replay) |

### 2. CUSTOMER_IDENTIFICATION

| Field | Value |
|-------|-------|
| **Node** | `customer_identification` |
| **Responsibility** | Load authenticated user profile |
| **Input** | `user_id: UUID` (from JWT) |
| **Output** | `customer_profile: CustomerProfile` |
| **Tool Call** | `get_customer_profile` |
| **LLM Call** | No |
| **Max Retries** | 2 |
| **Routes To** | ORDER_RESOLUTION |
| **Error Route** | FAILED |
| **Interruptible** | No |

### 3. ORDER_RESOLUTION

| Field | Value |
|-------|-------|
| **Node** | `order_resolution` |
| **Responsibility** | Find the order(s) the user is referring to |
| **Input** | `customer_profile`, `intent`, `extracted_entities`, `user_message` |
| **Output** | `candidate_orders: List[Order]`, `confirmed_order: Optional[Order]` |
| **Tool Calls** | `list_customer_orders` |
| **LLM Call** | Yes — to resolve which order from candidates |
| **Max Retries** | 1 |
| **Routes To** | FACT_COLLECTION (1 match), NEED_MORE_INFORMATION (0 or multiple matches) |
| **Error Route** | NEED_MORE_INFORMATION |
| **Interruptible** | No |

### 4. FACT_COLLECTION

| Field | Value |
|-------|-------|
| **Node** | `fact_collection` |
| **Responsibility** | Gather all facts: order detail, logistics, existing tickets |
| **Input** | `confirmed_order`, `customer_profile` |
| **Output** | `order_detail: OrderDetail`, `logistics: LogisticsRecord`, `existing_tickets: List[Ticket]` |
| **Tool Calls** | `get_order_detail`, `get_logistics_status`, `get_existing_after_sales_ticket` |
| **LLM Call** | No |
| **Max Retries** | 2 per tool |
| **Routes To** | POLICY_RETRIEVAL |
| **Error Route** | RETRY (then FAILED if exhausted) |
| **Interruptible** | No |

### 5. POLICY_RETRIEVAL

| Field | Value |
|-------|-------|
| **Node** | `policy_retrieval` |
| **Responsibility** | Search RAG for applicable after-sales policies |
| **Input** | `intent`, `order_detail`, `user_message` |
| **Output** | `policies: List[PolicyDocument]` (with scores) |
| **Tool Calls** | `search_after_sales_policy` |
| **LLM Call** | Yes — to construct optimal search query |
| **Max Retries** | 1 |
| **Routes To** | ELIGIBILITY_CHECK (policies found), ESCALATED (no policies) |
| **Error Route** | ESCALATED |
| **Interruptible** | No |

### 6. ELIGIBILITY_CHECK

| Field | Value |
|-------|-------|
| **Node** | `eligibility_check` |
| **Responsibility** | Deterministically check if user/order qualifies for the requested resolution |
| **Input** | `intent`, `order_detail`, `logistics`, `existing_tickets`, `customer_profile`, `policies` |
| **Output** | `eligibility: EligibilityResult`, `rejection_reason: Optional[str]` |
| **Tool Calls** | `check_after_sales_eligibility` (rule engine wrapper) |
| **LLM Call** | **NO** — pure deterministic code |
| **Max Retries** | 0 (deterministic) |
| **Routes To** | SOLUTION_GENERATION (eligible), COMPLETED (ineligible, explain to user) |
| **Error Route** | FAILED |
| **Interruptible** | No |

### 7. SOLUTION_GENERATION

| Field | Value |
|-------|-------|
| **Node** | `solution_generation` |
| **Responsibility** | Generate a resolution plan. LLM generates explanation; code calculates amounts. |
| **Input** | `intent`, `order_detail`, `policies`, `eligibility` |
| **Output** | `solution: Solution` (type, amount, items, explanation) |
| **LLM Call** | Yes — for explanation text and plan structure |
| **Code Calculation** | `calculate_refund_amount(order, policies)` — deterministic |
| **Max Retries** | 1 (LLM output validation) |
| **Routes To** | USER_CONFIRMATION |
| **Error Route** | FAILED |
| **Interruptible** | No |

### 8. USER_CONFIRMATION

| Field | Value |
|-------|-------|
| **Node** | `user_confirmation` |
| **Responsibility** | Present the plan and wait for user confirmation |
| **Input** | `solution` |
| **Output** | `confirmation: bool`, `user_feedback: Optional[str]` |
| **LLM Call** | No — waits for structured user response |
| **Max Retries** | 0 |
| **Routes To** | RISK_CHECK (confirmed), COMPLETED (rejected) |
| **Error Route** | N/A |
| **Interruptible** | **YES** — this is a natural pause point |
| **Resumable** | **YES** — resume with user's confirmation response |

### 9. RISK_CHECK

| Field | Value |
|-------|-------|
| **Node** | `risk_check` |
| **Responsibility** | Evaluate if the requested operation is high-risk |
| **Input** | `solution`, `customer_profile.risk_level`, `order_detail` |
| **Output** | `risk: RiskAssessment` (is_high_risk, reasons) |
| **Rule** | Amount > HIGH_RISK_THRESHOLD config, user risk_level = HIGH, certain product categories |
| **LLM Call** | **NO** — deterministic rules |
| **Max Retries** | 0 |
| **Routes To** | ACTION_EXECUTION (low risk), HUMAN_APPROVAL (high risk) |
| **Interruptible** | No |

### 10. HUMAN_APPROVAL

| Field | Value |
|-------|-------|
| **Node** | `human_approval` |
| **Responsibility** | Create approval task, pause agent, notify operator |
| **Input** | `solution`, `order_detail`, `risk`, `customer_profile` |
| **Output** | `approval_task: ApprovalTask` |
| **Tool Calls** | `create_approval_task` |
| **LLM Call** | No |
| **Max Retries** | 2 |
| **Routes To** | ACTION_EXECUTION (approved), COMPLETED (rejected) |
| **Interruptible** | **YES** — agent is paused here |
| **Resumable** | **YES** — resume on approval/rejection event |

### 11. ACTION_EXECUTION

| Field | Value |
|-------|-------|
| **Node** | `action_execution` |
| **Responsibility** | Execute the business operations: create ticket, refund, reshipment |
| **Input** | `solution`, `order_detail`, `customer_profile` |
| **Output** | `execution_results: List[ToolResult]` |
| **Tool Calls** | `create_after_sales_ticket`, `create_refund_request`, `create_reshipment_order`, `update_ticket_status`, etc. |
| **LLM Call** | No |
| **Max Retries** | 2 per tool (with exponential backoff) |
| **Routes To** | RESULT_VERIFICATION (success), RETRY (transient failure), FAILED (permanent failure) |
| **Interruptible** | No |

### 12. RESULT_VERIFICATION

| Field | Value |
|-------|-------|
| **Node** | `result_verification` |
| **Responsibility** | Verify the database state reflects execution results |
| **Input** | `execution_results` |
| **Output** | `verification: VerificationResult` (verified, mismatches) |
| **Tool Calls** | Re-query affected resources to confirm state |
| **LLM Call** | **NO** — code compares expected vs actual DB state |
| **Max Retries** | 2 (re-verify after retry) |
| **Routes To** | MEMORY_UPDATE (verified), RETRY (mismatch), FAILED (persistent mismatch) |
| **Interruptible** | No |

### 13. MEMORY_UPDATE

| Field | Value |
|-------|-------|
| **Node** | `memory_update` |
| **Responsibility** | Save short-term, long-term, and business state memories |
| **Input** | `session_id`, `user_id`, `execution_results`, `solution`, `policies_used` |
| **Output** | `memory_save_results` |
| **LLM Call** | Yes — to generate summaries for long-term memory |
| **Max Retries** | 2 |
| **Routes To** | COMPLETED |
| **Interruptible** | No |

### Terminal Nodes

**COMPLETED** — Successful completion. Returns final response to user.

**NEED_MORE_INFORMATION** — Agent asks user a clarifying question. Resumable.

**RETRY** — Retries preceding node. Tracks retry count; exceeds max → FAILED.

**ESCALATED** — Transferred to human operator. Creates escalation ticket.

**FAILED** — Terminal failure. Logs error, notifies user with safe fallback message.

## Graph State Schema

```python
class AgentState(TypedDict):
    # Session
    session_id: str
    thread_id: str
    user_id: str

    # Message
    user_message: str
    conversation_history: List[Message]

    # Current state
    current_node: str
    intent: Optional[str]
    confidence: Optional[float]
    extracted_entities: Optional[dict]

    # Customer & Order
    customer_profile: Optional[dict]
    candidate_orders: Optional[List[dict]]
    confirmed_order: Optional[dict]
    order_detail: Optional[dict]
    logistics: Optional[dict]
    existing_tickets: Optional[List[dict]]

    # Policy & Eligibility
    policies: Optional[List[dict]]
    eligibility: Optional[dict]
    rejection_reason: Optional[str]

    # Solution
    solution: Optional[dict]
    user_confirmed: Optional[bool]

    # Risk & Approval
    risk_assessment: Optional[dict]
    approval_task: Optional[dict]

    # Execution
    execution_results: Optional[List[dict]]
    verification: Optional[dict]

    # Control
    retry_count: int
    max_retries: int
    errors: List[dict]

    # Response
    agent_response: Optional[str]
    agent_context: Optional[dict]
```

## Routing Rules

```python
def route_after_order_resolution(state: AgentState) -> str:
    if state["confirmed_order"]:
        return "FACT_COLLECTION"
    return "NEED_MORE_INFORMATION"

def route_after_policy_retrieval(state: AgentState) -> str:
    if state["policies"] and len(state["policies"]) > 0:
        return "ELIGIBILITY_CHECK"
    return "ESCALATED"

def route_after_eligibility(state: AgentState) -> str:
    if state["eligibility"]["is_eligible"]:
        return "SOLUTION_GENERATION"
    return "COMPLETED"

def route_after_confirmation(state: AgentState) -> str:
    if state["user_confirmed"]:
        return "RISK_CHECK"
    return "COMPLETED"

def route_after_risk(state: AgentState) -> str:
    if state["risk_assessment"]["is_high_risk"]:
        return "HUMAN_APPROVAL"
    return "ACTION_EXECUTION"

def route_after_approval(state: AgentState) -> str:
    if state["approval_task"]["status"] == "APPROVED":
        return "ACTION_EXECUTION"
    return "COMPLETED"

def route_after_execution(state: AgentState) -> str:
    if state["execution_results"] and all(r["success"] for r in state["execution_results"]):
        return "RESULT_VERIFICATION"
    if state["retry_count"] < state["max_retries"]:
        return "RETRY"
    return "FAILED"

def route_after_verification(state: AgentState) -> str:
    if state["verification"]["is_verified"]:
        return "MEMORY_UPDATE"
    if state["retry_count"] < state["max_retries"]:
        return "RETRY"
    return "FAILED"
```

## Checkpointing & Resume

- LangGraph's built-in checkpointing saves state after each node.
- Nodes marked `Interruptible: YES` are natural breakpoints where the graph can be paused.
- The `HUMAN_APPROVAL` node creates a checkpoint before pausing.
- The admin approval endpoint triggers resume from the checkpoint.
- Session expiration is configurable; expired checkpoints are cleaned up.
