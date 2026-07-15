---
name: resolveai-review
description: Read-only review of the current diff. Checks scope, transactions, concurrency, permissions, data leaks, types, and test coverage. Does not modify code.
---

# ResolveAI Diff Review

Read-only review of uncommitted changes in the ResolveAI project.

## Workflow

1. Run `git diff --stat` and `git diff` to identify changed files.
2. Read every changed file in full.
3. Check against the active phase plan in `tasks/phase-04-rag.md`.
4. Report findings categorised by severity.

## Review Dimensions

### Scope
- Are changes within the declared batch scope?
- Any premature implementation of future phases?
- Any modification of old migrations (001–004)?

### Transactions & Concurrency
- Are DB sessions closed after use?
- Are embedding calls made without an open DB session?
- Are advisory locks used correctly (lock_timeout, re-read, release)?
- Any `SELECT ... FOR UPDATE` held across external calls?

### Permissions
- Are admin endpoints protected by `require_role("ADMIN")`?
- Are Agent tools restricted to correct `allowed_roles`?
- Any internal UUIDs or hashes leaked to API responses?

### Data Leaks
- Are LLM-bound fields projected through `sanitization.py`?
- Any PII or internal IDs in log messages?
- Vector search results: only allowed fields returned?

### Types
- All function signatures annotated?
- Pydantic v2 style (`model_validate`, not `parse_obj`)?
- SQLAlchemy 2 style (`select()`, not `Model.query`)?

### Tests
- New code covered by tests?
- Tests self-contained (no shared seed data)?
- Mock providers used (no real API keys)?
- Edge cases covered (empty input, error paths)?

## Output Format

### BLOCKER (must fix before commit)
- file:line — description

### IMPORTANT (should fix)
- file:line — description

### MINOR (consider)
- file:line — description

### Commit conditions met
- YES / NO (explain if NO)

## Rules

- **Read-only.** Do not modify any files.
- Do not run `git commit` or `git push`.

---

## Mandatory Final Response

Before ending the turn, always send a user-visible final report.
Never end immediately after reading the last file or after a search returns empty.
Even if no issues are found, output an explicit "no findings" report.
Do not wait for the user to ask for the report.

### Report Template

- **BLOCKER** — list or "None"
- **IMPORTANT** — list or "None"
- **MINOR** — list or "None"
- **Commit conditions met** — YES / NO

Keep the report concise. Do not repeat the full review dimensions.
