---
name: resolveai-batch
description: Implement a specific ResolveAI development batch. Reads project docs, enforces scope boundaries, runs quality gates, does not commit or push.
---

# ResolveAI Batch Implementation

Implement the user-specified Phase 04A/04B/04C development batch for the ResolveAI project.

Task details are passed via `$ARGUMENTS`.

## Workflow

### 1. Read Project Context

Before writing any code, read these files in order:

- `CLAUDE.md`
- `AGENTS.md`
- `tasks/active-phase.md`
- `tasks/phase-04-rag.md` (or current phase plan)
- Relevant source code for the batch
- Existing tests following the same pattern

### 2. Scope Enforcement

- **Only implement the explicitly specified batch.** Do not start the next batch early.
- Do not implement: new LangGraph nodes, Admin API (unless scoped), Agent Tools (unless scoped), policy data files (unless scoped), PDF/DOCX parsing (Phase 04C).
- Do not modify: old Alembic migrations, Phase 02/03 behavior, pyproject.toml (unless the batch explicitly requires a new dependency).
- Do not use: real API keys in tests (`LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`), `hash()` for deterministic vectors, Redis/Kafka/MCP.

### 3. Quality Gates

After implementation, the main agent must run these commands directly (do not delegate to a nested skill):

```bash
cd /Users/citlowl/Desktop/ResolveAI/backend
source .venv/bin/activate

python -m pip check
python -m ruff check app/ tests/
python -m mypy --no-incremental app/ tests/
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock python -m pytest -v

# Only if the batch includes a migration:
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

**All gates must pass.** Do not use skip, xfail, delete assertions, or lower strictness.

### 4. Subagent Rules

If a subagent (e.g., `resolveai-db-reviewer`, `resolveai-code-reviewer`) is used:

- **Wait for the subagent to complete** before proceeding.
- **Read its result** from the tool output.
- **Merge its conclusions** into this skill's final report.
- A subagent's output is **not** a substitute for the final report — the main session must produce its own user-visible report.

### 5. Rules

- **Do NOT run `git commit` or `git push`.**
- Do not start the next batch unless explicitly instructed.
- Do not modify planning documents unless updating status.

---

## Mandatory Final Response

Before ending the turn, always send a user-visible final report.
Never end immediately after a tool call, test command, subagent result, or error.
Even if the task is blocked, incomplete, or tests fail, output the required report.
Do not wait for the user to ask for the report.

### Report Template

1. **Files modified** — list every file added or changed
2. **Completed content** — what was implemented
3. **Test results** — `pip check` / `ruff` / `mypy` / `pytest` with total passed count
4. **Git status** — branch, uncommitted files, ahead/behind
5. **BLOCKER** — anything that must be fixed before commit
6. **Remaining issues** — anything not yet done
7. **Commit conditions met** — YES / NO

Keep the report concise. Do not repeat the task description. Do not output a verbose phase gate.
