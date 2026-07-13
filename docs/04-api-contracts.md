# 04 — API Contracts

## Base URL

```
http://localhost:8000/api/v1
```

## Common Patterns

### Response Envelope

All API responses follow this format:

```json
{
  "success": true,
  "code": "OK",
  "message": "描述信息",
  "data": {},
  "trace_id": "trace_xxx"
}
```

### Error Response

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "Human-readable error message",
  "data": null,
  "trace_id": "trace_xxx",
  "detail": {
    "errors": [{"field": "email", "message": "Invalid email format"}]
  }
}
```

### Pagination

```json
{
  "success": true,
  "code": "OK",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

### Authentication

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

## Endpoint Summary

### Auth (`/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register new user |
| POST | `/auth/login` | No | Login, get tokens |
| POST | `/auth/refresh` | No (refresh token) | Refresh access token |
| GET | `/auth/me` | Yes | Get current user profile |

### Products (`/products`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/products` | No | List products (paginated, filterable) |
| GET | `/products/{id}` | No | Get product detail |

### Orders (`/orders`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/orders` | Yes | CUSTOMER | Place a simulated order |
| GET | `/orders` | Yes | CUSTOMER | List my orders |
| GET | `/orders/{id}` | Yes | CUSTOMER | Get order detail |
| GET | `/orders/{id}/logistics` | Yes | CUSTOMER | Get logistics for order |
| GET | `/admin/orders` | Yes | OPERATOR, ADMIN | List all orders |
| GET | `/admin/orders/{id}` | Yes | OPERATOR, ADMIN | Get any order detail |

### After-Sales Tickets (`/tickets`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/tickets` | Yes | CUSTOMER | List my tickets |
| GET | `/tickets/{id}` | Yes | CUSTOMER | Get ticket detail |
| GET | `/admin/tickets` | Yes | OPERATOR, ADMIN | List all tickets |
| PATCH | `/admin/tickets/{id}` | Yes | OPERATOR, ADMIN | Update ticket |

### Agent (`/agent`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/agent/chat` | Yes | Send message to agent (HTTP) |
| WS | `/agent/ws` | Yes | Agent conversation (WebSocket) |
| GET | `/agent/sessions` | Yes | List my agent sessions |
| GET | `/agent/sessions/{id}` | Yes | Get session detail |
| GET | `/agent/sessions/{id}/messages` | Yes | Get session messages |

### Agent WebSocket Protocol

**Client → Server:**
```json
{
  "type": "message",
  "payload": {
    "content": "我的耳机还没发货，我不想要了",
    "thread_id": "thread_xxx"
  }
}
```

```json
{
  "type": "confirm",
  "payload": {
    "confirmation_id": "confirm_xxx",
    "accepted": true
  }
}
```

```json
{
  "type": "resume",
  "payload": {
    "session_id": "session_xxx"
  }
}
```

**Server → Client:**
```json
{
  "type": "message",
  "payload": {
    "role": "agent",
    "content": "您好，我查到您的订单...",
    "node": "SOLUTION_GENERATION",
    "context": {
      "intent": "PRE_SHIP_REFUND",
      "current_order": {},
      "policy_references": []
    }
  }
}
```

```json
{
  "type": "confirmation_request",
  "payload": {
    "confirmation_id": "confirm_xxx",
    "plan": {},
    "message": "请确认是否进行退款？"
  }
}
```

```json
{
  "type": "status_update",
  "payload": {
    "node": "HUMAN_APPROVAL",
    "status": "等待人工审批",
    "estimated_wait": "2小时内"
  }
}
```

### Admin (`/admin`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/admin/dashboard` | Yes | OPERATOR, ADMIN | Dashboard metrics |
| GET | `/admin/approvals` | Yes | OPERATOR, ADMIN | List approval tasks |
| POST | `/admin/approvals/{id}/approve` | Yes | OPERATOR, ADMIN | Approve task |
| POST | `/admin/approvals/{id}/reject` | Yes | OPERATOR, ADMIN | Reject task |
| GET | `/admin/traces` | Yes | ADMIN | List agent traces |
| GET | `/admin/traces/{trace_id}` | Yes | ADMIN | Get trace detail |
| GET | `/admin/tool-logs` | Yes | ADMIN | List tool call logs |
| GET | `/admin/audit-logs` | Yes | ADMIN | List audit logs |

### Policies (`/admin/policies`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/admin/policies` | Yes | ADMIN | List policies |
| POST | `/admin/policies` | Yes | ADMIN | Create policy |
| GET | `/admin/policies/{id}` | Yes | ADMIN | Get policy detail |
| PUT | `/admin/policies/{id}` | Yes | ADMIN | Update policy (creates new version) |
| PATCH | `/admin/policies/{id}/status` | Yes | ADMIN | Change policy status |

### Config (`/admin/config`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/admin/config` | Yes | ADMIN | List all configs |
| PUT | `/admin/config/{key}` | Yes | ADMIN | Update config |

### Evaluations (`/admin/evaluations`)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/admin/evaluations` | Yes | ADMIN | List evaluation runs |
| POST | `/admin/evaluations/run` | Yes | ADMIN | Trigger evaluation run |
| GET | `/admin/evaluations/{id}` | Yes | ADMIN | Get evaluation results |

## Status Codes

| Code | Name | Typical Use |
|------|------|-------------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Wrong role |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate, idempotency conflict, invalid state transition |
| 422 | Unprocessable Entity | Business rule violation |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Server Error | Unexpected error |
| 503 | Service Unavailable | LLM or DB down |

## Error Codes

| Code | Description |
|------|-------------|
| `OK` | Success |
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_ERROR` | Invalid credentials |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `CONFLICT` | Resource conflict |
| `IDEMPOTENCY_CONFLICT` | Duplicate idempotent request |
| `INVALID_STATE_TRANSITION` | Illegal status change |
| `BUSINESS_RULE_VIOLATION` | Violates business rules |
| `RATE_LIMITED` | Too many requests |
| `LLM_ERROR` | LLM service error |
| `RAG_ERROR` | RAG retrieval error |
| `TOOL_ERROR` | Tool execution error |
| `INTERNAL_ERROR` | Unexpected server error |
