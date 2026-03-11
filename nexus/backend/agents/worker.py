import asyncio
import logging
import re
import traceback
from pathlib import Path

from backend.agents.models import WorkerResult, WorkerTask
from backend.core.event_bus import EventBus
from backend.models.events import EventType, NexusEvent
from backend.services.ollama_client import OllamaClient
from backend.services.shell import BASH, run_shell

log = logging.getLogger("nexus.worker")

ALLOWED_COMMANDS = {"grep", "sed", "cat", "find", "head", "tail", "wc"}
SHELL_TIMEOUT = 15.0
RAW_CAP = 4000


class WorkerAgent:
    def __init__(self, ollama: OllamaClient, bus: EventBus):
        self.ollama = ollama
        self.bus = bus

    async def run(
        self,
        task: WorkerTask,
        session_id: str,
        codebase_path: Path,
        worker_timeout: int = 60,
    ) -> WorkerResult:
        log.info("[%s] spawning  cmd=%r  cwd=%s", task.task_id, task.command, codebase_path)

        await self.bus.emit(NexusEvent(
            type=EventType.WORKER_SPAWN,
            session_id=session_id,
            data={"task_id": task.task_id, "description": task.description, "command": task.command},
        ))

        try:
            async with asyncio.timeout(worker_timeout):
                return await self._execute(task, session_id, codebase_path)
        except TimeoutError:
            log.warning("[%s] timed out after %ds", task.task_id, worker_timeout)
            await self.bus.emit(NexusEvent(
                type=EventType.WORKER_TIMEOUT,
                session_id=session_id,
                data={"task_id": task.task_id},
            ))
            return WorkerResult(task_id=task.task_id, success=False, error="worker timeout")
        except Exception as e:
            tb = traceback.format_exc()
            msg = str(e) or repr(e)
            log.error("[%s] FAILED  %s: %s\n%s", task.task_id, type(e).__name__, msg, tb)
            await self.bus.emit(NexusEvent(
                type=EventType.WORKER_FAILED,
                session_id=session_id,
                data={"task_id": task.task_id, "error": f"{type(e).__name__}: {msg}"},
            ))
            return WorkerResult(task_id=task.task_id, success=False, error=f"{type(e).__name__}: {msg}")

    async def _execute(self, task: WorkerTask, session_id: str, codebase_path: Path) -> WorkerResult:
        raw = await self._shell(task.command, codebase_path)
        log.info("[%s] shell done  lines=%d", task.task_id, len(raw.splitlines()))

        await self.bus.emit(NexusEvent(
            type=EventType.WORKER_COMMAND,
            session_id=session_id,
            data={
                "task_id": task.task_id,
                "command": task.command,
                "output_lines": len(raw.splitlines()),
            },
        ))

        if not raw.strip():
            log.info("[%s] empty output", task.task_id)
            return WorkerResult(task_id=task.task_id, success=True, raw_output="", formatted="No results found.")

        prompt = (
            f"Shell command: {task.command}\n"
            f"Goal: {task.description}\n\n"
            f"Output:\n{raw[:RAW_CAP]}\n\n"
            "Summarize key findings as bullet points. "
            "For each finding include the file path and line number as 'path/file.py:42'. "
            "Maximum 10 bullets. Be concise."
        )

        log.info("[%s] sending to Ollama (%d chars prompt)", task.task_id, len(prompt))
        formatted, tok_in, tok_out = await self.ollama.complete(prompt=prompt)
        log.info("[%s] Ollama done  tok_in=%d tok_out=%d", task.task_id, tok_in, tok_out)

        citations = extract_grep_citations(raw) or extract_citations(formatted)
        log.info("[%s] citations=%s", task.task_id, citations[:5])

        result = WorkerResult(
            task_id=task.task_id,
            success=True,
            raw_output=raw,
            formatted=formatted,
            citations=citations,
            tokens_in=tok_in,
            tokens_out=tok_out,
        )

        await self.bus.emit(NexusEvent(
            type=EventType.WORKER_RESULT,
            session_id=session_id,
            data={
                "task_id": task.task_id,
                "citations": citations[:10],
                "tok_in": tok_in,
                "tok_out": tok_out,
            },
        ))
        return result

    async def _shell(self, command: str, cwd: Path) -> str:
        cmd_name = command.strip().split()[0]
        if cmd_name not in ALLOWED_COMMANDS:
            raise ValueError(f"Disallowed command: {cmd_name!r}")
        log.debug("shell  bash=%s  cmd=%r  cwd=%s", BASH, command, cwd)
        return await run_shell(command, cwd, timeout=SHELL_TIMEOUT)


# ── Helpers ──────────────────────────────────────────────────────────────────

_CITATION_RE = re.compile(r'[\w./\\-]+\.(?:py|js|ts|go|rs|java|c|cpp|h|rb):\d+')
_GREP_LINE_RE = re.compile(r'^([\w./\\-]+\.(?:py|js|ts|go|rs|java|c|cpp|h|rb)):(\d+):')


def extract_citations(text: str) -> list[str]:
    return list(dict.fromkeys(_CITATION_RE.findall(text)))


def extract_grep_citations(raw: str) -> list[str]:
    results: list[str] = []
    for line in raw.splitlines():
        m = _GREP_LINE_RE.match(line)
        if m:
            results.append(f"{m.group(1)}:{m.group(2)}")
    return list(dict.fromkeys(results))
