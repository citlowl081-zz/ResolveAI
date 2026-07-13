# ADR-003: LangGraph Explicit State Machine over Free-Form ReAct Agent

## Status
Accepted

## Context
We need to choose an agent architecture. The agent must follow a specific business process (intent → identity → order → facts → policy → eligibility → solution → confirm → risk → approve → execute → verify), handle interruptions, support human-in-the-loop, and be debuggable. We must choose between a free-form ReAct loop and an explicit state machine.

## Decision
Use LangGraph to implement an explicit state machine with 16 named nodes and deterministic routing, rather than a free-form ReAct agent with tool-calling autonomy.

## Alternatives Considered

### Free-Form ReAct Agent (LangChain AgentExecutor or similar)
- **Pros:** Flexible, can handle unexpected scenarios, less code to write upfront.
- **Cons:** Unpredictable execution path. Cannot guarantee the agent checks eligibility before creating a refund. Cannot enforce human approval for high-risk operations. Hard to debug — tracing is opaque. Hard to test deterministically. LLM might "hallucinate" tool results or skip verification steps.

### LangGraph with Single Agent Node + Conditional Edges
- **Pros:** Some structure while maintaining flexibility.
- **Cons:** The agent node is still a black box. Routing from a single node is complex and hard to validate.

### Pure Finite State Machine (no LLM)
- **Pros:** Fully deterministic, provably correct.
- **Cons:** Cannot handle natural language input. Loses the key advantage of LLMs for intent understanding and natural conversation.

## Why LangGraph Explicit State Machine?
1. **Predictable flow:** Every execution follows the same path through defined nodes. The agent cannot skip eligibility check or verification.
2. **Deterministic routing:** Edge conditions are Python code (`if state["risk"]["is_high_risk"]:`), not LLM decisions.
3. **LLM scoped to NLU tasks:** The LLM only runs in nodes that need natural language understanding (intent classification, order resolution, solution explanation, memory summarization). It never decides routing or calculates amounts.
4. **Built-in checkpointing:** LangGraph checkpoints save state after every node, enabling pause/resume for human approval and cross-session continuation.
5. **Debuggability:** Every node's input/output is traced. The exact path through the graph is recorded. This is critical for a demo project where you must explain what happened.
6. **Testability:** Each node can be tested in isolation with mocked inputs. Routing logic is unit-testable.
7. **Interview-friendly:** "We chose an explicit state machine over free-form ReAct because..." is a strong architectural narrative.

## Consequences

### Easier
- Predictable, auditable execution paths.
- Deterministic routing that cannot be "hallucinated" or skipped.
- Clear separation of LLM tasks (NLU) from code tasks (math, rules, DB).
- Each node is independently testable.
- Human-in-the-loop is a first-class concept (checkpoint → pause → resume).

### More Difficult
- Adding a new intent type requires adding the appropriate routing rules (but this is a feature — it forces conscious design).
- The state machine is opinionated — edge cases that don't fit the flow may need custom handling.

## Node-to-LLM Responsibility Map

| Node | LLM Used? | Why |
|------|-----------|-----|
| INTENT_CLASSIFICATION | Yes | NLU: classify user message |
| CUSTOMER_IDENTIFICATION | No | DB query only |
| ORDER_RESOLUTION | Yes | NLU: match "my headphones" to an order |
| FACT_COLLECTION | No | Tool calls only |
| POLICY_RETRIEVAL | Yes | NLU: generate optimal search query |
| ELIGIBILITY_CHECK | **No** | Deterministic rules |
| SOLUTION_GENERATION | Yes | NLU: explain the plan |
| USER_CONFIRMATION | No | Wait for user input |
| RISK_CHECK | **No** | Deterministic rules |
| HUMAN_APPROVAL | No | Create task, wait |
| ACTION_EXECUTION | No | Tool calls only |
| RESULT_VERIFICATION | **No** | Code compares DB state |
| MEMORY_UPDATE | Yes | NLU: summarize for memory |

## References
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
