import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.config import settings
from backend.models.schemas import (
    HealthResponse,
    IndexRequest,
    IndexResponse,
    QueryRequest,
    QueryResponse,
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
    worker_ok = await _ollama.model_available(settings.worker_model) if ollama_ok else False
    manager_ok = await _ollama.model_available(settings.manager_model) if ollama_ok else False

    return HealthResponse(
        status="ok",
        anthropic=bool(settings.anthropic_api_key),
        ollama=ollama_ok,
        models={
            settings.worker_model: worker_ok,
            settings.manager_model: manager_ok,
        },
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


# ── Query ─────────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def start_query(req: QueryRequest, background_tasks: BackgroundTasks):
    """
    Kick off the NEXUS pipeline. Returns immediately with a session_id.
    Connect to /ws/{session_id} to receive all events and the streamed response.
    """
    from backend.core.orchestrator import orchestrator  # lazy import avoids circular deps

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
