# Phase 06 — Human Approval System

## Phase Goals

Implement the human approval workflow: risk-based escalation, approval task creation, admin review interface, and agent resume after decision. This is the "human-in-the-loop" component.

## Preconditions

- Phase 03 completed (agent state machine with HUMAN_APPROVAL node).
- Phase 02 completed (approval service and API).
- Phase 05 completed (business state memory for tracking pending approvals).

## Task Checklist

### 6.1 Risk Assessment
- [ ] `rules/risk.py` — Deterministic risk scoring.
- [ ] Factors: order amount, user risk level, product category, refund history.
- [ ] Configurable threshold via system_configs.
- [ ] Risk level output: LOW, MEDIUM, HIGH.

### 6.2 Approval Task Management
- [ ] `services/approval_service.py` — Create, list, process.
- [ ] Assign to operator or admin based on risk level.
- [ ] Approval context includes full ticket and solution data.
- [ ] Decision: APPROVE or REJECT with mandatory notes.

### 6.3 Agent Pause & Resume
- [ ] HUMAN_APPROVAL node: create approval task, save checkpoint, pause.
- [ ] Agent notifies user with wait time estimate.
- [ ] Admin processes approval → triggers agent resume.
- [ ] Agent loads checkpoint, reads decision, continues or ends.

### 6.4 Admin API
- [ ] GET `/admin/approvals` — list pending and completed.
- [ ] GET `/admin/approvals/{id}` — detail with context.
- [ ] POST `/admin/approvals/{id}/approve` — approve with note.
- [ ] POST `/admin/approvals/{id}/reject` — reject with reason.

### 6.5 Notifications (Simulated)
- [ ] On approval created: log event (future: push to admin).
- [ ] On approval decided: log event, resume agent session.
- [ ] On agent resume: notify user.

### 6.6 Testing
- [ ] Risk assessment unit tests.
- [ ] Approval creation and processing tests.
- [ ] Agent pause and resume workflow tests.
- [ ] Rejection flow tests (agent explains rejection to user).
- [ ] Admin permission tests (operator vs admin access).
- [ ] Idempotency: duplicate approval processing prevented.

## Acceptance Criteria

- [ ] High-risk operations correctly trigger HUMAN_APPROVAL node.
- [ ] Agent saves state and pauses when awaiting approval.
- [ ] Admin can view pending approvals with full context.
- [ ] Admin can approve or reject with required notes.
- [ ] Approved operations resume agent execution.
- [ ] Rejected operations gracefully end with explanation.
- [ ] Audit logs track all approval decisions.
- [ ] All tests pass.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
