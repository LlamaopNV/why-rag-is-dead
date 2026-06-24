import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.config import settings
from backend.models.schemas import (
    BenchmarkInput,
    HealthResponse,
    IndexRequest,
    IndexResponse,
    QueryRequest,
    QueryResponse,
    RaceRequest,
)
from backend.services.anthropic_client import AnthropicClient
from backend.services.indexer import indexer
from backend.services.ollama_client import OllamaClient

router = APIRouter(prefix="/api")

_anthropic = AnthropicClient()
_ollama = OllamaClient()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    ollama_ok = await _ollama.health_check()
    worker_ok  = await _ollama.model_available(settings.worker_model)  if ollama_ok else False
    manager_ok = await _ollama.model_available(settings.manager_model) if ollama_ok else False

    return HealthResponse(
        status="ok",
        anthropic=bool(settings.anthropic_api_key),
        ollama=ollama_ok,
        models={settings.worker_model: worker_ok, settings.manager_model: manager_ok},
        codebase_indexed=indexer.indexed,
    )


# ── Codebase Index ────────────────────────────────────────────────────────────

@router.post("/index", response_model=IndexResponse)
async def index_codebase(req: IndexRequest):
    try:
        return indexer.index(req.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/status")
async def index_status():
    if not indexer.indexed:
        return {"indexed": False}
    return {
        "indexed": True,
        "path": str(indexer.codebase_path),
        "file_count": len(indexer.file_index),
        "total_lines": indexer.total_lines,
        "naive_token_estimate": indexer.naive_token_estimate(),
    }


@router.get("/index/files")
async def get_files():
    if not indexer.indexed:
        raise HTTPException(status_code=400, detail="Codebase not indexed yet")
    return {"files": indexer.get_file_list(), "count": len(indexer.file_index)}


# ── NEXUS query ───────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def start_query(req: QueryRequest, background_tasks: BackgroundTasks):
    from backend.core.orchestrator import orchestrator

    if not indexer.indexed and not req.codebase_path:
        raise HTTPException(status_code=400, detail="No codebase indexed. POST /api/index first.")

    session_id = req.session_id or str(uuid.uuid4())
    background_tasks.add_task(
        orchestrator.run,
        req.query,
        session_id,
        req.codebase_path,
        req.naive_mode,
    )
    return QueryResponse(session_id=session_id)


# ── Benchmark ─────────────────────────────────────────────────────────────────

@router.get("/benchmark/status")
async def benchmark_status():
    """Check whether Claude Code CLI is installed and available."""
    from backend.services.claude_code_benchmark import benchmark_service
    return {
        "available": benchmark_service.is_available(),
        "claude_binary": benchmark_service.claude_bin,
    }


@router.post("/benchmark/race")
async def race_query(req: RaceRequest, background_tasks: BackgroundTasks):
    """
    Run the same query through NEXUS and Claude Code CLI simultaneously.
    Both stream events to /ws/{session_id} in real-time.
    """
    from backend.core.orchestrator import orchestrator
    from backend.services.claude_code_benchmark import benchmark_service
    from backend.services.indexer import indexer
    from pathlib import Path

    if not indexer.indexed and not req.codebase_path:
        raise HTTPException(status_code=400, detail="No codebase indexed. POST /api/index first.")
    if not benchmark_service.is_available():
        raise HTTPException(status_code=400, detail="Claude Code CLI not found. Install with: npm i -g @anthropic-ai/claude-code")

    session_id = req.session_id or str(uuid.uuid4())
    cb_path = Path(req.codebase_path) if req.codebase_path else indexer.codebase_path

    async def _run():
        await asyncio.gather(
            orchestrator.run(req.query, session_id, req.codebase_path),
            benchmark_service.run_query(req.query, session_id, cb_path),
            return_exceptions=True,
        )

    background_tasks.add_task(_run)
    return {"session_id": session_id, "status": "race_started"}


@router.post("/benchmark/manual")
async def manual_benchmark(data: BenchmarkInput):
    """Store a manually-entered Claude Code CLI result (fallback if CLI not installed)."""
    from backend.core.event_bus import event_bus
    from backend.models.events import EventType, NexusEvent

    # Store in a simple module-level dict keyed by a constant key
    # (single active benchmark — last one wins)
    from backend.services.claude_code_benchmark import benchmark_service
    benchmark_service._manual = data.model_dump()

    # Emit so any connected WebSocket session can pick it up (no session-specific here)
    # Frontend handles this by polling or by the user refreshing the budget display
    return {"status": "ok", "data": data.model_dump()}


# ── Token stats ───────────────────────────────────────────────────────────────

@router.get("/tokens/{session_id}")
async def get_tokens(session_id: str):
    from backend.core.context_tracker import context_tracker
    stats = context_tracker.get(session_id)
    return {
        **stats.model_dump(),
        "total_nexus": stats.total_nexus,
        "reduction_pct": stats.reduction_pct,
    }
