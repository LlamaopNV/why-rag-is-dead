import asyncio
import logging
import traceback
from pathlib import Path

from backend.agents.models import VerifiedContext, VerifiedFact, WorkerResult, WorkerTask
from backend.agents.worker import WorkerAgent, extract_grep_citations, extract_citations
from backend.config import settings
from backend.core.context_tracker import context_tracker
from backend.core.event_bus import EventBus
from backend.models.events import EventType, NexusEvent
from backend.services.ollama_client import OllamaClient
from backend.services.shell import run_shell

log = logging.getLogger("nexus.manager")

MAX_FACTS = 30          # cap facts sent to main LLM
SED_TIMEOUT = 5.0       # seconds per verification command


class ManagerAgent:
    def __init__(self, ollama: OllamaClient, bus: EventBus):
        self.ollama = ollama
        self.bus = bus
        self._worker = WorkerAgent(ollama, bus)

    async def run(
        self,
        tasks: list[WorkerTask],
        session_id: str,
        codebase_path: Path,
    ) -> VerifiedContext:
        # ── Fan-out: all workers in parallel ──────────────────────────────────
        results: list[WorkerResult] = list(
            await asyncio.gather(
                *[self._worker.run(t, session_id, codebase_path, settings.worker_timeout) for t in tasks],
                return_exceptions=False,
            )
        )

        # Track worker tokens
        for r in results:
            if r.success:
                context_tracker.update_worker(session_id, r.tokens_in, r.tokens_out)

        # ── Collect citations from all successful workers ──────────────────────
        # Map citation → task_id (grep output preferred over SLM extraction)
        all_citations: dict[str, str] = {}
        for result in results:
            if not result.success:
                continue
            # Deterministic first
            for c in extract_grep_citations(result.raw_output):
                all_citations[c] = result.task_id
            # SLM-extracted as fallback (don't overwrite grep hits)
            for c in extract_citations(result.formatted):
                all_citations.setdefault(c, result.task_id)

        await self.bus.emit(NexusEvent(
            type=EventType.MANAGER_VERIFY,
            session_id=session_id,
            data={"total_citations": len(all_citations)},
        ))

        # ── Verify each citation with sed ─────────────────────────────────────
        facts: list[VerifiedFact] = []
        # Process up to 2× MAX_FACTS candidates so we can fill MAX_FACTS after failures
        candidates = list(all_citations.items())[: MAX_FACTS * 2]
        verify_jobs = [
            self._verify(citation, task_id, codebase_path, session_id)
            for citation, task_id in candidates
        ]
        verify_results = await asyncio.gather(*verify_jobs, return_exceptions=True)

        for vr in verify_results:
            if isinstance(vr, VerifiedFact):
                facts.append(vr)
                if len(facts) >= MAX_FACTS:
                    break

        await self.bus.emit(NexusEvent(
            type=EventType.MANAGER_PACKAGE,
            session_id=session_id,
            data={
                "verified": len(facts),
                "dropped": len(all_citations) - len(facts),
                "token_estimate": VerifiedContext(facts=facts).token_estimate(),
            },
        ))

        return VerifiedContext(facts=facts)

    async def _verify(
        self,
        citation: str,
        task_id: str,
        codebase_path: Path,
        session_id: str,
    ) -> VerifiedFact | None:
        """Verify a file:line citation using sed. Returns None if unverifiable."""
        parts = citation.rsplit(":", 1)
        if len(parts) != 2:
            return None

        rel_path, lineno_str = parts
        try:
            lineno = int(lineno_str)
        except ValueError:
            return None

        abs_path = codebase_path / rel_path
        if not abs_path.exists():
            await self.bus.emit(NexusEvent(
                type=EventType.MANAGER_VERIFY_FAIL,
                session_id=session_id,
                data={"citation": citation, "reason": "file not found"},
            ))
            return None

        # Fetch the cited line + 1 line of context either side
        start = max(1, lineno - 1)
        end = lineno + 1
        sed_cmd = f"sed -n '{start},{end}p' \"{rel_path}\""

        try:
            content = (await run_shell(sed_cmd, codebase_path, timeout=SED_TIMEOUT)).strip()
        except Exception as e:
            tb = traceback.format_exc()
            reason = f"{type(e).__name__}: {e}"
            log.error("verify FAILED  citation=%s  %s\n%s", citation, reason, tb)
            await self.bus.emit(NexusEvent(
                type=EventType.MANAGER_VERIFY_FAIL,
                session_id=session_id,
                data={"citation": citation, "reason": reason},
            ))
            return None

        if not content:
            await self.bus.emit(NexusEvent(
                type=EventType.MANAGER_VERIFY_FAIL,
                session_id=session_id,
                data={"citation": citation, "reason": "empty line"},
            ))
            return None

        lines = content.splitlines()
        target_idx = lineno - start           # 0-indexed offset within the sed window
        line_content = lines[target_idx] if target_idx < len(lines) else lines[0]
        context_lines = "\n".join(lines) if len(lines) > 1 else ""

        await self.bus.emit(NexusEvent(
            type=EventType.MANAGER_VERIFY_OK,
            session_id=session_id,
            data={"citation": citation},
        ))

        return VerifiedFact(
            citation=citation,
            line_content=line_content.strip(),
            context_lines=context_lines,
            source_task_id=task_id,
        )
