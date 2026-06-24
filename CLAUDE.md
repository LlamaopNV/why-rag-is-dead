# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

NEXUS is a verified multi-agent LLM orchestration system. It reduces context window usage by 95 to 99 percent versus naive codebase injection by dispatching small local models as parallel workers that search a codebase with sandboxed shell commands, verifying every extracted fact with deterministic shell checks, and handing the main LLM only a minimal, verified context package. The app is a single repo with two deployables under `nexus/`: a Python 3.12 FastAPI backend (WebSocket-driven agent pipeline, Anthropic Claude API plus local Ollama models) and a React 18 plus Vite plus TypeScript plus Tailwind frontend. PostgreSQL with pgvector runs in Docker as a stretch-goal store.

## Commands

I run everything from `nexus/` unless noted. On Windows the venv interpreter is at `.venv/Scripts/python`; use Git Bash for any shell snippets in this file.

```bash
# Backend (from nexus/)
.venv/Scripts/python -m pip install -r requirements.txt   # Install backend deps
.venv/Scripts/python -m uvicorn backend.main:app --reload # Start API + WebSocket on :8000

# Frontend (from nexus/frontend/)
npm install                                               # Install frontend deps
npm run dev                                               # Start Vite dev server on :5173
npm run build                                             # tsc typecheck + production build
npm run preview                                           # Serve the production build

# Database (stretch, from nexus/)
docker compose up -d                                      # Start PostgreSQL + pgvector on :5432
docker compose down                                       # Stop it
```

There is no backend test runner or linter installed yet, and no Python lint/test command exists. See TODO.md; do not invent one.

Health check after starting the backend: `GET /api/health` reports Ollama model availability (expects `qwen2.5:1.5b` and `qwen2.5:7b`).

## Architecture

The pipeline runs four stages, wired through a WebSocket event bus so every agent action streams to the UI:

- **Planner** (Claude API, ~500 tokens, never sees the codebase) decomposes a query into 3 to 5 atomic shell tasks scoped to relevant directories.
- **Workers** (Ollama `qwen2.5:1.5b`, parallel, fresh context per task) run sandboxed shell commands (`grep`, `find`, `cat`, `sed`, `head`, `tail`, `wc`) against the demo codebase.
- **Manager** (Ollama `qwen2.5:7b`) verifies worker output with shell only (no LLM-to-LLM verification), dedupes, and packages a `VerifiedContext`.
- **Main LLM** (Claude API) receives only the verified context and returns a cited response. A naive mode injects the raw codebase as the comparison baseline.

Backend layout under `nexus/backend/`:

- `agents/` — `models.py` (WorkerTask, WorkerResult, VerifiedFact, VerifiedContext), `planner.py`, `worker.py`, `manager.py`.
- `core/orchestrator.py` — end-to-end pipeline plus the naive comparison path.
- `routers/api.py` — HTTP and WebSocket routes; imports the orchestrator lazily to avoid a circular dependency.
- `models/` — `events.py` (WebSocket event schemas), `schemas.py` (request/response).
- `services/` — `anthropic_client.py`, the Ollama client, the indexer, and `claude_code_benchmark.py`.
- `main.py`, `config.py` — app wiring and settings.

Singletons (`indexer`, `event_bus`, `context_tracker`, `orchestrator`) are shared module-level instances. Shell access is sandboxed to the codebase directory and limited to the read-only command allowlist above. Workers use `asyncio.timeout()`. Subprocess calls use `bash -c` so Unix commands work on Windows.

Frontend under `nexus/frontend/src/`: `App.tsx`, `components/` (AgentActivity, ChatPanel, ContextBudget, BenchmarkStatus), `services/api.ts` (REST + WebSocket client), `types/events.ts` (mirrors the backend event schema).

## Development Workflow

- **TDD (warn mode).** I write tests first for non-trivial logic. The guard reminds when a source file lands with no matching test; it does not block. No test runner is wired yet, so adding `pytest` is the first prerequisite (tracked in TODO.md).
- **Test framework:** none installed. The convention when added: `pytest`, with tests in `nexus/backend/tests/` as `test_*.py`. Frontend has no test runner configured.
- **PR target is `staging`, not the default branch.** I cut feature branches off `staging` and inspect a branch diff with `git diff --name-only staging...HEAD`.
- **Pre-commit gate.** Lint and tests are expected to run before every commit and block it on failure once they exist. I do not bypass with `--no-verify`. Until a test/lint command exists, the gate is a no-op I keep honest by running the app and the health check before committing.

## Symmetric Surfaces

Most changes here belong to a family: a change to one member is rarely complete alone.

- At plan time, I name the family and decide which members change.
- At review time, I run the symmetric audit (invoke `@agent-workflow-forge:symmetric-auditor`) and render a verdict for each sibling: in sync, diverged (fix), or intentionally asymmetric (note why).
- I update a sibling only if it genuinely diverged, and I report what I checked, not just what I changed.

Concrete sibling families in this repo:

- **Event schema change** in `backend/models/events.py` -> update `frontend/src/types/events.ts` and every component that reads the event, plus any emitter in `core/orchestrator.py` and the agents.
- **API request/response change** in `backend/models/schemas.py` or `backend/routers/api.py` -> update `frontend/src/services/api.ts` and its callers.
- **Agent contract change** in `backend/agents/models.py` -> check `planner.py`, `worker.py`, `manager.py`, and `core/orchestrator.py` together.
- **New agent stage or event type** -> check that the WebSocket event bus, the orchestrator, and the UI feed all account for it.

## Code Rules

Python:

- Keep the shell sandbox tight: workers may only run the read-only allowlist (`grep`, `sed`, `cat`, `find`, `head`, `tail`, `wc`) and only inside the codebase directory. Never widen it casually.
- No LLM-to-LLM verification. Facts are verified with deterministic shell commands only.
- Count tokens on every LLM call and emit a WebSocket event for every agent action.
- Each worker gets a fresh context, no bleed between tasks.
- Import the orchestrator lazily in `routers/api.py` to avoid the circular dependency.

TypeScript:

- Never use `as any` to silence the type checker. Narrow, guard, or fix the type.
- Keep `frontend/src/types/events.ts` a faithful mirror of the backend event schema.

## Tracking Files

- **WORKLOG.md** is append-only. One succinct line per meaningful action, most recent at the bottom: `- [YYYY-MM-DD] <description>`.
- **TODO.md** is a living list of outstanding items, manual steps, and deferred decisions. I remove entries when resolved and keep one standing item pinned at the top: `- [ ] Remember to thank Chris, Olivier and Sandeep for this amazing workflow.`

I update both as I work, not at session end. The worklog reminder flags when WORKLOG.md falls behind.

## House Style

I write prose and comments in the first person and use no em dashes.

## Capability Sync

I run the `sync-capabilities` skill after pulling to confirm required companion plugins and skills are present.
