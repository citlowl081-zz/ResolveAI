# 08 — Security Design

## Security Principles

1. **Defense in Depth** — Multiple layers: auth, authorization, input validation, idempotency, audit logging, PII masking.
2. **Server-Side Enforcement** — All security checks happen on the backend. The frontend only hides UI elements for UX.
3. **Least Privilege** — Each role has the minimum permissions needed.
4. **Secure by Default** — Sensitive operations require explicit checks; defaults are restrictive.
5. **Never Trust the LLM** — LLM output is treated as untrusted input; all critical decisions use deterministic code.

## Authentication

### JWT Token Flow

```
1. User registers or logs in → receives access_token + refresh_token
2. access_token: short-lived (30 min), used in Authorization header
3. refresh_token: long-lived (7 days), used to get new access_token
4. Token contains: {sub: user_id, role: user_role, exp: timestamp}
```

### Implementation

- Passwords hashed with `bcrypt` (via `passlib`).
- JWT signed with HS256 (configurable to RS256 for production).
- `JWT_SECRET_KEY` must be at least 32 characters.
- Token blacklisting not required for v1.0 (short TTL suffices).

## Authorization

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **CUSTOMER** | View own orders, logistics, tickets; chat with agent; confirm/decline plans |
| **OPERATOR** | View all orders/tickets; process standard approvals; view agent traces |
| **ADMIN** | Full access: all OPERATOR permissions + policy management, config, evaluation, high-risk approvals, audit logs |

### Enforcement Points

1. **API Router Level:** Dependency injection checks JWT and role.
```python
@router.get("/admin/orders")
async def list_all_orders(
    current_user: User = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN))
):
    ...
```

2. **Service Level:** Services check ownership where applicable.
```python
async def get_order_detail(order_id: UUID, user: User) -> Order:
    order = await order_repo.get_by_id(order_id)
    if user.role == UserRole.CUSTOMER and order.user_id != user.id:
        raise AuthorizationError("Not your order")
    return order
```

3. **Agent Tool Level:** Tools validate that the calling agent has permission for the operation.
   - Every sensitive tool receives `user_id` from the LangGraph state (set during CUSTOMER_IDENTIFICATION from the verified JWT).
   - Tools call Service layer methods, which re-verify ownership (e.g., `user_id` matches `order.user_id`).
   - The agent cannot impersonate users — `user_id` is set once at session start and never modified by LLM nodes.
   - Tool-level permission errors are treated as potential security violations and logged at WARN level.

## Input Validation

### API Level
- All request bodies validated via Pydantic v2 schemas.
- String lengths, numeric ranges, enum values all constrained.
- SQL injection prevented by SQLAlchemy parameterized queries.
- XSS prevented by frontend framework (React) escaping.

### Agent Level
- User messages screened for Prompt injection patterns.
- Structured output from LLM validated against Pydantic schemas.
- Tool parameters validated before execution.

### Prompt Injection Detection

```python
INJECTION_PATTERNS = [
    r"ignore (all |your |previous )?instructions",
    r"system prompt",
    r"you are now",
    r"act as",
    r"bypass",
    r"override",
    r"forget",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
]

def detect_injection(message: str) -> bool:
    message_lower = message.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, message_lower):
            return True
    # Also check for excessive length, repeated tokens, etc.
    return False
```

If injection detected:
- Log the attempt (sanitized).
- Return a polite refusal.
- Flag the user's risk level.
- Do NOT pass the message to the LLM.

## Sensitive Operations

Operations that modify business state must include ALL of:

1. **Permission Check** — Does the caller have the right role?
2. **Input Validation** — Are all parameters valid?
3. **Idempotency Key** — Prevents duplicate execution.
4. **Database Transaction** — All-or-nothing execution.
5. **State Transition Validation** — Is this a legal status change?
6. **Audit Log** — Record who did what, when.
7. **Result Verification** — Did the database actually change?

### Idempotency

Idempotency keys are generated from `(operation_type, resource_id, item_ids, date)`:

```python
def generate_idempotency_key(operation: str, order_id: UUID, item_ids: list[UUID] | None = None) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    item_part = "_".join(sorted(str(i) for i in (item_ids or [])))
    if item_part:
        return f"{operation}_{order_id}_{item_part}_{today}"
    return f"{operation}_{order_id}_{today}"
```

This allows per-item idempotency — a refund for item A and a refund for item B on the same order on the same day have different keys and don't block each other.

Before executing:
```python
existing = await repo.find_by_idempotency_key(key)
if existing:
    return success_response(existing, code="IDEMPOTENT_REPLAY")
```

## Data Protection

### PII Masking in Logs

| Field | Masking Rule |
|-------|-------------|
| Password | Not logged (never) |
| API Key | Not logged (never) |
| JWT Token | Not logged (never) |
| Email | `u***r@example.com` |
| Phone | `138****5678` |
| Address | `北京市****` |
| Full Name | `张**` |

### Sensitive Data in API Responses

- Never return `hashed_password`.
- Never return internal IDs when not needed.
- Responses tailored to role (e.g., admin sees more).

## Error Handling

- Never expose stack traces to the client in production.
- Internal errors return generic "Internal Server Error" with a trace_id.
- Validation errors return field-level details.
- Authentication errors return generic "Invalid credentials" (don't reveal if email exists).

## Rate Limiting

- Authentication endpoints: 5 attempts per minute per IP.
- Agent chat: 20 messages per minute per user.
- API endpoints: 60 requests per minute per user (configurable).

## Security Checklist (Per-Phase)

Before completing any phase:
- [ ] No secrets in code.
- [ ] No PII in logs.
- [ ] All endpoints have auth checks (except public).
- [ ] All inputs validated.
- [ ] Sensitive operations use idempotency keys.
- [ ] Audit logs created for state changes.
- [ ] Prompt injection detection active on agent endpoints.
- [ ] Rate limiting configured (or explicitly disabled for dev).
