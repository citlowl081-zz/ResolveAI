---
name: resolveai-verify
description: Verify the current uncommitted batch. Runs pip check, ruff, mypy, pytest from backend/ with correct rootdir. Does not commit or push.
---

# ResolveAI Batch Verification

Verify that the current uncommitted development batch passes all quality gates.

## Critical: Run From `backend/`

**Always `cd` into `backend/` before running pytest.** Running from the repo root causes `asyncio_mode=auto` to be missed, producing false failures.

## Verification Steps

```bash
cd /Users/citlowl/Desktop/ResolveAI/backend
source .venv/bin/activate

# 1. Dependency check
python -m pip check

# 2. Lint
python -m ruff check app/ tests/

# 3. Type check (full app + tests, not just new files)
python -m mypy --no-incremental app/ tests/

# 4. Full test suite (correct rootdir is essential)
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock python -m pytest -v
```

### Migration Cycle (Only If Migration Was Added)

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Rules

- **Never run pytest from the repo root.**
- Use `EMBEDDING_PROVIDER=mock` — no real embedding API keys.
- Use `LLM_PROVIDER=mock` — no real LLM API keys.
- Full `mypy --no-incremental app/ tests/` — not just new files.
- No skip, no xfail, no deleting assertions, no lowering strictness.
- **Do NOT run `git commit` or `git push`.**

---

## Mandatory Final Response

Before ending the turn, always send a user-visible final report.
Never end immediately after a tool call, test command, or error.
Even if verification fails, output the report with the failure details.
Do not wait for the user to ask for the report.

### Report Template

1. **Actual scope** — changed files summary
2. **pip check** — PASS or the exact error
3. **Ruff** — PASS or error count + first error
4. **Mypy** — PASS with source file count, or error count + first error
5. **Pytest** — passed / failed / total, list any failures
6. **Migration cycle** — result (or N/A)
7. **Git status** — branch, uncommitted files
8. **Commit conditions met** — YES / NO
9. **Remaining issues** — anything unresolved

Keep the report concise.
