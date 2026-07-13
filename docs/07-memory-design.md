# 07 — Memory Design

## Overview

ResolveAI implements a three-tier memory system:

1. **Short-Term Memory** — Session-scoped. Tracks current conversation state, tool calls, and pending actions.
2. **Long-Term Memory** — User-scoped. Summarizes history, preferences, and patterns across sessions.
3. **Business State Memory** — Cross-session. Tracks active tickets, pending approvals, refunds, and commitments.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Memory System                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐                                   │
│  │  Agent Session    │                                   │
│  │  (LangGraph State)│  ◄── Short-Term Memory            │
│  │                   │      (in-process, per-session)    │
│  │  - current_node   │                                   │
│  │  - intent         │                                   │
│  │  - confirmed_order│                                   │
│  │  - solution       │                                   │
│  │  - tool_results   │                                   │
│  └───────┬───────────┘                                   │
│          │                                               │
│          │ On session end / checkpoint                   │
│          ▼                                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │           customer_memories Table                  │   │
│  │                                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ SHORT_TERM  │  │ LONG_TERM   │  │ BUSINESS   │ │   │
│  │  │ MEMORY      │  │ MEMORY      │  │ STATE      │ │   │
│  │  │             │  │             │  │ MEMORY     │ │   │
│  │  │ TTL: 1hr    │  │ TTL: ∞      │  │ TTL: ∞     │ │   │
│  │  │             │  │             │  │ (until     │ │   │
│  │  │             │  │             │  │ resolved)  │ │   │
│  │  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 1. Short-Term Memory (Session)

### Purpose
Track the current agent session's transient state.

### What's Stored
```python
class ShortTermMemory:
    session_id: str
    user_id: str
    thread_id: str

    # Current intent & entities
    intent: Optional[str]
    confidence: Optional[float]
    extracted_entities: Optional[dict]

    # Order resolution
    candidate_orders: Optional[List[dict]]
    confirmed_order_id: Optional[str]

    # Tool call history (this session)
    tool_calls: List[dict]  # [{tool_name, input, output, timestamp}]

    # Current state
    current_node: str
    proposed_solution: Optional[dict]
    pending_confirmation_id: Optional[str]
    pending_approval_id: Optional[str]

    # Error tracking
    retry_counts: dict  # {node_name: count}
    errors: List[dict]

    # Pending user actions
    awaiting_user_input: bool
    expected_input_type: Optional[str]  # "confirmation", "clarification", etc.
```

### Storage

Short-term memory exists in two synchronized layers:

1. **LangGraph agent state** (in-memory during session) — the authoritative copy during active conversation. Updated after every node execution.

2. **`agent_sessions.graph_state`** (JSONB, persisted at each checkpoint) — the durable copy. LangGraph's built-in checkpointing serializes the full agent state (including all short-term memory fields) to this column after every node transition.

3. **`customer_memories` table** (SHORT_TERM rows, optional) — a lightweight cross-session cache. On session end or checkpoint, key short-term fields (current intent, confirmed order, pending confirmations) are also upserted to `customer_memories` with `memory_type = 'SHORT_TERM'`. This enables a new session (within TTL) to pick up context even if the original `agent_sessions` row has expired. The LangGraph checkpoint in `agent_sessions.graph_state` remains the authoritative source for full session restore.

- **TTL:** Configurable, default 60 minutes. Expired sessions and their SHORT_TERM memory rows are cleaned up.

### Behavior
- Created when user starts a new conversation.
- Updated after every node execution.
- Cleared when session completes or expires.
- On resume: restored from `agent_sessions.graph_state` (primary) or reconstructed from `customer_memories` SHORT_TERM rows (fallback).

## 2. Long-Term Memory (User)

### Purpose
Remember user characteristics, preferences, and history across sessions.

### What's Stored
```python
class LongTermMemory:
    user_id: str

    # Preferences
    communication_style: str       # "concise", "detailed", etc.
    preferred_solution_type: str   # "refund", "exchange", etc.
    preferred_contact_method: str  # "chat", "phone"

    # History summary
    total_tickets: int
    total_refunds: int
    last_ticket_summary: Optional[str]
    frequent_issue_types: List[str]

    # Risk profile
    risk_level: str                # LOW, MEDIUM, HIGH
    refund_dispute_count: int
    chargeback_count: int

    # Common data
    default_shipping_address: Optional[str]
    saved_phone: Optional[str]

    # Important events (last N)
    recent_tickets: List[dict]  # [{ticket_id, date, type, outcome}]
```

### Storage
- `customer_memories` table with `memory_type = 'LONG_TERM'`.
- One row per `(user_id, key)` pair.
- Updated after each completed agent session.

### LLM Summarization
- After each session, LLM generates a summary of what happened.
- Summary is merged into existing long-term memory.
- Source (session_id, timestamp) is always recorded.

### Behavior
- Loaded at the start of CUSTOMER_IDENTIFICATION node.
- Agent uses long-term memory to personalize responses.
- Updated at MEMORY_UPDATE node after session completion.

## 3. Business State Memory (Cross-Session)

### Purpose
Track in-progress business operations that span sessions.

### What's Stored
```python
class BusinessStateMemory:
    user_id: str

    # Active tickets
    active_tickets: List[str]        # ticket_ids

    # Pending operations
    pending_approvals: List[str]     # approval_task_ids
    pending_refunds: List[str]       # refund_record_ids
    pending_reshipments: List[str]   # reshipment_order_ids

    # Commitments made to user
    commitments: List[dict]          # [{description, promised_at, fulfilled}]

    # Awaiting actions
    waiting_for_user_confirmation: List[str]  # confirmation_ids
    waiting_for_return_shipping: bool
    waiting_for_inspection: bool

    # Current state summary
    last_session_summary: str
    last_agent_node: str
```

### Storage
- `customer_memories` table with `memory_type = 'BUSINESS_STATE'`.
- One row per `(user_id, key)` pair.
- Updated at MEMORY_UPDATE node.

### Behavior
- **Most important check:** On session start, agent queries business state first to see if there are existing tickets, pending approvals, or pending commitments.
- Prevents duplicate actions: agent checks if a refund/reshipment already exists before creating a new one.
- Handles cross-session continuation: user can say "我的东西发了吗？" and agent reads the existing reshipment state.

## Memory Update Flow

```
Session Start
    │
    ├── Load Long-Term Memory (personalization)
    ├── Load Business State (prevent duplicates, resume pending)
    │
Session Processing (LangGraph nodes)
    │
    ├── Short-Term Memory updated in LangGraph state
    │
MEMORY_UPDATE Node (post-execution)
    │
    ├── Update Business State Memory
    │   ├── Save new ticket references
    │   ├── Save pending approval references
    │   ├── Mark commitments
    │   └── Clear fulfilled items
    │
    ├── Update Long-Term Memory
    │   ├── LLM generates session summary
    │   ├── Merge into user history
    │   └── Update risk indicators
    │
    └── Persist to customer_memories table
```

## Key Design Rules

1. **Isolation:** Memory is isolated by `user_id` and `thread_id`. User A cannot read User B's memories.

2. **Source Tracking:** Every memory entry records its source (session_id, event, or system).

3. **No Raw Chat History as Memory:** Do not stuff entire conversation history into memory. Always summarize.

4. **Priority on Business State:** On every new session, check business state first. An active ticket or pending approval takes priority over new intent classification.

5. **Deduplication:** Before creating a refund or reshipment, check business state memory and the database for existing records. Idempotency keys provide a second layer of protection.

6. **Expiration:** Short-term memories auto-expire; business state memories persist until the associated operation is completed; long-term memories persist indefinitely but are summarized/compressed.

## Prohibited Memory Anti-Patterns

- ❌ Stuffing raw chat history into the prompt as the only "memory".
- ❌ Not checking for existing tickets/refunds before creating new ones.
- ❌ Forgetting commitments across sessions.
- ❌ Keeping short-term memory data beyond session expiration.
- ❌ Using LLM to "remember" facts that should be in the database.
