# Phase 07 — Frontend

## Phase Goals

Build the customer-facing web application and the admin dashboard using Next.js, TypeScript, Tailwind CSS, and shadcn/ui. The frontend must clearly display agent workflow state, not just a chat box.

## Preconditions

- Phase 02 completed (backend APIs).
- Phase 03 completed (agent WebSocket endpoint).
- Node.js 20+ installed.

## Task Checklist

### 7.1 Customer Web Setup
- [ ] Initialize Next.js 14 project with TypeScript.
- [ ] Configure Tailwind CSS and shadcn/ui.
- [ ] Set up React Query for API state management.
- [ ] Create API client with Zod validation.
- [ ] Auth context and protected routes.

### 7.2 Customer Pages
- [ ] Login/Register page.
- [ ] Product list page (with category filter).
- [ ] Product detail page.
- [ ] Order creation (simulated checkout).
- [ ] Order list page.
- [ ] Order detail page (with logistics timeline).
- [ ] Agent chat page — the core page.

### 7.3 Agent Chat UI
- [ ] WebSocket connection management.
- [ ] Chat message display (user + agent + system).
- [ ] **Current intent display** — show which intent was classified.
- [ ] **Current order card** — show the resolved order.
- [ ] **Policy citation display** — show which policies were referenced.
- [ ] **Confirmation dialog** — Accept/Decline the proposed solution.
- [ ] **Approval status indicator** — "Awaiting human approval".
- [ ] **Progress tracker** — Visual indicator of current agent node.
- [ ] Typing indicator during agent processing.

### 7.4 After-Sales Progress Page
- [ ] Ticket list for current user.
- [ ] Ticket detail with timeline.
- [ ] Refund/reshipment status.
- [ ] Approval status.

### 7.5 Admin Web Setup
- [ ] Initialize Next.js 14 project with TypeScript.
- [ ] Configure Tailwind CSS and shadcn/ui.
- [ ] Admin auth (same API, admin role required).

### 7.6 Admin Pages
- [ ] Dashboard — key metrics overview.
- [ ] Order management — list all orders.
- [ ] Ticket management — list, filter, detail.
- [ ] **Approval Center** — pending, approved, rejected.
- [ ] **Policy Management** — CRUD with versioning.
- [ ] **Agent Trace Viewer** — graph visualization of execution path.
- [ ] **Tool Call Logs** — table with filters.
- [ ] **Audit Logs** — table with filters.
- [ ] **Evaluation Results** — metrics dashboard.
- [ ] System Configuration — edit key-value configs.

### 7.7 Testing
- [ ] Component tests (React Testing Library).
- [ ] Page-level integration tests.
- [ ] WebSocket mock for agent chat tests.
- [ ] Accessibility checks.

### 7.8 Build & Quality
- [ ] `npm run lint` passes.
- [ ] `npm run typecheck` passes.
- [ ] `npm run build` passes.
- [ ] No hardcoded API URLs (use env vars).

## Acceptance Criteria

- [ ] Customer can register, browse, order, and chat with agent.
- [ ] Agent chat shows intent, order, policy, and progress.
- [ ] Confirmation dialog works (accept/decline).
- [ ] Approval flow is visible in admin.
- [ ] Admin can manage policies, view traces, and process approvals.
- [ ] Both frontends build successfully.
- [ ] All lint, typecheck, and test pass.

## Completion Record

- **Started:** 2026-07-15
- **Phase 07A Completed:** 2026-07-15
- **Phase 07B (WeChat) Completed:** 2026-07-15
- **Phase 07 Overall:** COMPLETE
