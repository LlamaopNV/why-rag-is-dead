# NEXUS — Verified Multi-Agent Code Search

NEXUS is a multi-agent LLM orchestration system that reduces context window usage by **95–99%** compared to naive codebase injection, while independently verifying every fact it returns.

> "What if your LLM could prove where every answer came from, and use 80–95% less context doing it?"

---

## How It Works

Instead of stuffing an entire codebase into one LLM call, NEXUS dispatches small language models as parallel workers to search and extract only what's needed, verifies every claim with deterministic shell commands, and delivers a minimal verified context package to the main LLM.

```
User Query
    ↓
PLANNER (Claude API — ~500 tokens, never sees the codebase)
    Decomposes query into 3–5 atomic shell tasks, scoped to relevant directories
    ↓
WORKERS (Ollama qwen2.5:1.5b — parallel, fresh context per task)
    Execute sandboxed shell commands (grep, find, cat, sed)
    Format results into structured citations
    ↓
MANAGER (deterministic shell verification)
    Runs sed -n '{line}p' on every citation to confirm it exists
    Deduplicates, filters, packages minimal verified context
    ↓
MAIN LLM (Claude API — receives ONLY verified context)
    Reasons over verified facts, returns response with source citations
    ↓
Response with provenance — every claim linked to a verified file:line
```

---

## Token Comparison

| Approach | Tokens | Notes |
|---|---|---|
| Naive (dump relevant files) | ~50K+ | No verification, no scoping |
| Claude Code | ~53K | Smart but reads whole files |
| **NEXUS** | **~13K** | Verified facts only |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, WebSocket |
| Planner + Main LLM | Claude API (claude-sonnet-4-6) |
| Workers | Ollama qwen2.5:1.5b |
| Manager verification | bash (grep, sed, find) |
| Frontend | React + Vite + Tailwind CSS |
| Database | PostgreSQL + pgvector (Docker) |

---

## Prerequisites

- Python 3.13
- Node.js 18+
- [Ollama](https://ollama.com) with models pulled:
  ```
  ollama pull qwen2.5:1.5b
  ollama pull qwen2.5:7b
  ```
- Git for Windows (provides bash/grep/sed on Windows)
- Anthropic API key

---

## Setup

### 1. Clone and configure

```bash
git clone <repo>
cd WarpDev-Context-Demo
```

Copy and fill in your API key:
```bash
cp nexus/.env.example nexus/.env
# Edit nexus/.env — set ANTHROPIC_API_KEY
```

### 2. Backend

```powershell
cd nexus
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend

```powershell
cd nexus\frontend
npm install
```

### 4. Ollama parallelism (important for speed)

Set before starting Ollama to allow workers to run concurrently:
```powershell
$env:OLLAMA_NUM_PARALLEL=7
ollama serve
```

---

## Running

**Terminal 1 — Backend:**
```powershell
cd nexus
.venv\Scripts\python -m uvicorn backend.main:app --reload
```

**Terminal 2 — Frontend:**
```powershell
cd nexus\frontend
npm run dev
```

Open **http://localhost:5173**

1. Enter your codebase path in the **Codebase** box and click **Index**
2. Ask a question about your code
3. Watch agents work in the right panel — citations verified in real time
4. Compare NEXUS token usage vs naive file dump in the Context Budget

---

## Project Structure

```
nexus/
├── docker-compose.yml          # PostgreSQL + pgvector
├── requirements.txt
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings (pydantic-settings + .env)
│   ├── agents/
│   │   ├── planner.py          # Claude API → task decomposition
│   │   ├── worker.py           # Shell execution + Ollama formatting
│   │   ├── manager.py          # sed verification + context packaging
│   │   └── models.py           # WorkerTask, VerifiedContext schemas
│   ├── core/
│   │   ├── orchestrator.py     # End-to-end pipeline
│   │   ├── event_bus.py        # WebSocket broadcast
│   │   └── context_tracker.py  # Per-session token ledger
│   ├── services/
│   │   ├── anthropic_client.py # Claude API with streaming + token counting
│   │   ├── ollama_client.py    # Ollama API wrapper
│   │   ├── indexer.py          # Codebase file walker
│   │   └── shell.py            # Platform-aware bash discovery + executor
│   ├── models/
│   │   ├── events.py           # NexusEvent + EventType enum
│   │   └── schemas.py          # REST request/response schemas
│   └── routers/
│       ├── api.py              # REST endpoints
│       └── ws.py               # WebSocket /ws/{session_id}
└── frontend/
    └── src/
        ├── App.tsx             # Main state + WebSocket session management
        ├── components/
        │   ├── ChatPanel.tsx   # Query input + streaming response
        │   ├── AgentActivity.tsx # Real-time event feed
        │   ├── ContextBudget.tsx # Token comparison bars
        │   ├── Settings.tsx    # Codebase path + index
        │   └── StatusBar.tsx   # Health indicators
        ├── hooks/
        │   └── useWebSocket.ts # Callback-ref WS hook with keepalive
        ├── services/
        │   └── api.ts          # Typed REST client
        └── types/
            └── events.ts       # TypeScript event types mirroring backend
```

---

## Key Design Decisions

- **Shell verification, not LLM verification** — the manager confirms citations with `sed`, not by asking another model
- **Fresh context per worker** — every Ollama call starts with zero history, no bleed between tasks
- **Token counting everywhere** — every Claude and Ollama call is tracked
- **WebSocket as single source of truth** — `POST /api/query` returns immediately; all results stream through `/ws/{session_id}`
- **Sandboxed commands** — workers can only run `grep`, `sed`, `cat`, `find`, `head`, `tail`, `wc`

---

## Branches

| Branch | Description |
|---|---|
| `main` | Workers: qwen2.5:1.5b · Manager: shell-only verification |
| `feature/7b-manager` | Manager uses qwen2.5:7b for semantic ranking + verification |
