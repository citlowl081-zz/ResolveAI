# Demonstration Scripts

## 5-Minute Demo Walkthrough

### Preparation
```bash
docker compose up -d
# Wait for health checks to pass
# Open http://localhost:3000 (Customer) and http://localhost:3001 (Admin)
```

### Flow (5 min)

**1. Customer Login & Orders (1 min)**
- Open Customer Web → Login: `demo@example.com` / `demo123456`
- Navigate to "我的订单" — show 3 orders with different statuses
- Click ORD-000003 (SHIPPED) — show logistics tracking

**2. Agent Policy Consultation (1 min)**
- Navigate to "智能客服"
- Type: "退货政策是什么？"
- Show: Agent responds with structured citations (policy_key + version + title)
- Explain: RAG retrieved relevant policies from pgvector

**3. Agent After-Sales Flow (1.5 min)**
- Type: "我要退款，收到的耳机有质量问题"
- Show: Agent proposes refund action
- Click "确认执行"
- Show: PENDING_APPROVAL status (high refund amount triggers approval)

**4. Admin Approval (1 min)**
- Open Admin Web → Login: `admin@example.com` / `admin123456`
- Show Dashboard: ticket count + pending approvals
- Navigate to "审批中心"
- Show: PENDING approval for the refund
- Click "批准" → Status changes to APPROVED
- Click "执行操作" → Ticket created, refund processed

**5. Memory Demo (30 sec)**
- Back to Customer Web → "记住我偏好支付宝退款"
- Navigate to "我的记忆" — show the new PREFERENCE memory
- Start new agent session → agent has loaded this preference

### Key Points to Highlight
- Citations always come from real policy documents (never fabricated)
- Approval payload is DB-stored, not client-submitted
- Optimistic locking prevents double-approval
- Tool idempotency prevents double-refund

## 10-Minute Technical Deep-Dive

### Architecture Overview (2 min)
```
1. System Architecture diagram
2. LangGraph 9-node state machine
3. Tool Calling with pending_action flow
4. RAG Pipeline with pgvector
```

### Key Design Decisions (3 min)
1. **LLM never computes money** — refund amounts from deterministic calculator
2. **No DB during LLM calls** — separate TX boundaries
3. **Optimistic locking** on all mutating entities
4. **Data minimization** — field allowlists for LLM, PII stripping
5. **Idempotency** — API-level (Idempotency-Key) + Tool-level (SHA256)

### Code Walkthrough (3 min)
1. `AgentOrchestrator.run()` — preflight → approval gate → LangGraph → TX-B
2. `compose_response._build_citations()` — only from real tool_results
3. `RefundService.execute_refund()` — lock ordering, cumulative cap
4. `ApprovalTaskRepository.decide()` — optimistic locking SQL

### Testing & Quality (2 min)
- 525 backend tests (0 failures)
- 22 Playwright E2E tests (Customer 14 + Admin 8, all passing)
- RAG: HitRate@5=0.952, MRR=0.775
- Memory: Write Accuracy 1.0, False-Write Avoidance 0.833

## Demo Data Checklist

- [ ] PostgreSQL running with pgvector
- [ ] Backend healthy (http://localhost:8000/health)
- [ ] Customer Web (http://localhost:3000)
- [ ] Admin Web (http://localhost:3001)
- [ ] 10 demo products seeded
- [ ] 3 demo orders (DELIVERED, PAID, SHIPPED)
- [ ] 24 policies ingested with embeddings
- [ ] Demo agent session exists
- [ ] Mock LLM provider configured for the default demo, or local Qwen credentials configured for the optional real-model demo

## Screenshot Checklist

Customer Web:
- [ ] Login page
- [ ] Home page with navigation grid
- [ ] Product list
- [ ] Order list with status badges
- [ ] Order detail with logistics
- [ ] Agent chat with citations
- [ ] Agent chat with proposed action + confirm/cancel
- [ ] Agent chat with PENDING_APPROVAL
- [ ] Memories page
- [ ] Approvals page

Admin Web:
- [ ] Login page
- [ ] Dashboard
- [ ] Ticket list with filters
- [ ] Approval center with PENDING/APPROVED/REJECTED
- [ ] Policy list
- [ ] Agent Traces table
- [ ] Tool Logs table

## Common Interview Questions

**Q: Why LangGraph instead of a simple chain?**
A: LangGraph provides explicit state management and node routing. The 9-node graph gives deterministic control flow — we know exactly which node runs when. This is critical for audit trails and reliability.

**Q: How do you prevent the LLM from fabricating refund amounts?**
A: The LLM classifies intent and proposes actions with natural keys (product names). The `PendingActionBuilder` resolves these to internal UUIDs and the `RefundCalculator` computes amounts deterministically. The LLM never sees or computes money.

**Q: How do you handle concurrent approval decisions?**
A: Optimistic locking. The `decide()` method does `UPDATE ... WHERE version=X AND status='PENDING'`. The second concurrent decision gets 0 rows affected and returns a conflict.

**Q: What happens if the LLM call fails mid-turn?**
A: The orchestrator classifies the exception. Terminal errors complete the turn with an error message. Recoverable errors preserve the turn identity so the client can retry with the same idempotency key.

**Q: How does RAG citation work?**
A: Citations are built from real `tool_results` — the `_build_citations()` function only reads from `search_after_sales_policy` results. If no policy search ran, citations is an empty list. We never let the LLM fabricate policy references.
