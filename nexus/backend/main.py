import asyncio
import logging
import sys

# Windows requires ProactorEventLoop for subprocess support.
# Must be set before any event loop is created.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
# Promote nexus loggers to DEBUG so we see shell commands
logging.getLogger("nexus").setLevel(logging.DEBUG)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.api import router as api_router
from backend.routers.ws import router as ws_router


_log = logging.getLogger("nexus.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.services.shell import BASH, run_shell
    from backend.services.claude_code_benchmark import benchmark_service
    from backend.core.event_bus import event_bus
    from pathlib import Path

    # Wire event_bus into benchmark singleton
    benchmark_service.bus = event_bus

    _log.info("NEXUS starting  bash=%s", BASH)
    _log.info("Claude Code CLI: %s", benchmark_service.claude_bin or "NOT FOUND")

    try:
        out = await run_shell("echo nexus-shell-ok", Path("."), timeout=5.0)
        _log.info("shell smoke-test: %s", out.strip())
    except Exception as e:
        _log.error("shell smoke-test FAILED: %s", e)

    yield

    from backend.routers.api import _ollama
    await _ollama.close()
    _log.info("NEXUS stopped.")


app = FastAPI(title="NEXUS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"service": "NEXUS", "version": "0.1.0", "docs": "/docs"}
