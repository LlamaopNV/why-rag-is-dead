"""
Claude Code CLI benchmark service.

claude -p --output-format json --verbose outputs a single JSON array to stdout,
fully buffered until the process exits. There is no real-time streaming.

Strategy:
  1. Run the process in a thread-pool executor (blocks until done)
  2. Parse the JSON array
  3. Emit tool-call progress events (all at once after completion)
  4. Emit the final stats + response text
"""
import asyncio
import json
import logging
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from backend.core.event_bus import EventBus
from backend.models.events import EventType, NexusEvent
from backend.services.indexer import indexer

log = logging.getLogger("nexus.benchmark")

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nexus-bench")
TIMEOUT = 180   # seconds


class ClaudeCodeBenchmark:
    def __init__(self, bus: Optional[EventBus]):
        self.bus = bus
        self.claude_bin = shutil.which("claude")
        self._manual: Optional[dict] = None

    def is_available(self) -> bool:
        return self.claude_bin is not None

    async def run_query(
        self,
        query: str,
        session_id: str,
        codebase_path: Optional[Path] = None,
    ) -> dict:
        path = codebase_path or indexer.codebase_path
        if not path:
            await self._emit(session_id, EventType.BENCHMARK_ERROR, {"error": "No codebase path"})
            return {"error": "no codebase path"}

        if not self.is_available():
            await self._emit(session_id, EventType.BENCHMARK_ERROR, {"error": "claude CLI not found"})
            return {"error": "claude CLI not found"}

        log.info("benchmark: starting  cwd=%s", path)
        await self._emit(session_id, EventType.BENCHMARK_STARTED, {
            "query": query,
            "tool": "Claude Code CLI",
        })

        loop = asyncio.get_running_loop()
        start = time.time()

        def _run_sync() -> tuple[str, float]:
            cmd = [self.claude_bin, "-p", query, "--output-format", "json", "--verbose"]
            proc = subprocess.Popen(
                cmd,
                cwd=str(path),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            try:
                stdout, _ = proc.communicate(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                stdout = ""
            elapsed = time.time() - start
            return stdout, elapsed

        try:
            stdout, elapsed = await asyncio.wait_for(
                loop.run_in_executor(_POOL, _run_sync),
                timeout=TIMEOUT + 15,
            )
        except asyncio.TimeoutError:
            log.warning("benchmark: timed out after %ds", TIMEOUT)
            await self._emit(session_id, EventType.BENCHMARK_TIMEOUT, {"timeout": TIMEOUT})
            return {"error": "timeout"}

        log.info("benchmark: process done in %.1fs, parsing output (%d chars)", elapsed, len(stdout))

        # Parse the JSON array output
        try:
            events: list[dict] = json.loads(stdout.strip())
            if not isinstance(events, list):
                events = []
        except (json.JSONDecodeError, ValueError):
            log.warning("benchmark: failed to parse output as JSON array")
            events = []

        # Emit tool-call events and collect response text
        tool_count = 0
        result_obj: dict = {}

        for obj in events:
            obj_type = obj.get("type", "")

            if obj_type == "result":
                result_obj = obj

            ev = _parse_event(obj)
            if ev is None:
                continue

            if ev["type"] == "tool_use":
                tool_count += 1
                await self._emit(session_id, EventType.BENCHMARK_PROGRESS, ev)

            elif ev["type"] == "assistant_text":
                # Emit the response text so the frontend can display it
                await self._emit(session_id, EventType.BENCHMARK_STREAM, {"chunk": ev["text"]})

        result = _extract_stats(result_obj, elapsed, tool_count)
        log.info(
            "benchmark: done  tokens=%d  tools=%d  time=%.1fs  cost=$%.4f",
            result["total_tokens"], result["tool_calls"], result["time_seconds"],
            result.get("cost_usd", 0),
        )

        await self._emit(session_id, EventType.BENCHMARK_COMPLETE, {
            "tokens":       result["total_tokens"],
            "tool_calls":   result["tool_calls"],
            "time_seconds": result["time_seconds"],
            "model":        result.get("model", ""),
            "cost_usd":     result.get("cost_usd", 0),
        })
        return result

    async def _emit(self, session_id: str, type_: EventType, data: dict):
        if self.bus:
            await self.bus.emit(NexusEvent(type=type_, session_id=session_id, data=data))


# ── Event parsers ─────────────────────────────────────────────────────────────

def _parse_event(obj: dict) -> Optional[dict]:
    """Extract a displayable event from a claude NDJSON/array object."""
    obj_type = obj.get("type", "")

    if obj_type == "assistant":
        for item in obj.get("message", {}).get("content", []):
            if item.get("type") == "tool_use":
                name = item.get("name", "")
                preview = _compact_input(name, item.get("input", {}))
                return {"type": "tool_use", "tool_name": name, "preview": preview}
            if item.get("type") == "text":
                text = item.get("text", "").strip()
                if text:
                    return {"type": "assistant_text", "text": text}

    elif obj_type == "user":
        for item in obj.get("message", {}).get("content", []):
            if item.get("type") == "tool_result":
                return {"type": "tool_result"}

    return None


def _compact_input(name: str, inp: dict) -> str:
    if name in ("Read",):       return (inp.get("file_path") or "")[-60:]
    if name in ("Grep",):       return f"{inp.get('pattern','')!r} in {inp.get('path','.')}"
    if name == "Glob":          return inp.get("pattern", "")
    if name == "Bash":          return (inp.get("command") or "")[:60]
    vals = list(inp.values())
    return str(vals[0])[:60] if vals else ""


def _extract_stats(result_obj: dict, elapsed: float, tool_count: int) -> dict:
    usage = result_obj.get("usage", {})
    inp  = usage.get("input_tokens", 0)
    cc   = usage.get("cache_creation_input_tokens", 0)
    cr   = usage.get("cache_read_input_tokens", 0)
    out  = usage.get("output_tokens", 0)
    total = inp + cc + cr + out

    model_name = ""
    for m_name, m_data in result_obj.get("modelUsage", {}).items():
        model_name = m_name
        t = (m_data.get("inputTokens", 0) + m_data.get("outputTokens", 0)
             + m_data.get("cacheReadInputTokens", 0) + m_data.get("cacheCreationInputTokens", 0))
        if t > 0:
            total = t
        break

    duration_ms = result_obj.get("duration_ms", int(elapsed * 1000))
    return {
        "total_tokens": total,
        "tool_calls":   tool_count or result_obj.get("num_turns", 0),
        "time_seconds": round(duration_ms / 1000, 1),
        "model":        model_name,
        "cost_usd":     result_obj.get("total_cost_usd", 0),
        "response":     result_obj.get("result", "")[:500],
    }


# Singleton — bus injected at startup in main.py lifespan
benchmark_service = ClaudeCodeBenchmark(bus=None)
