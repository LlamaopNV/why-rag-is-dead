import asyncio
import json
import logging
import re
import traceback
from pathlib import Path

from backend.agents.models import VerifiedContext, VerifiedFact, WorkerTask
from backend.agents.worker import WorkerAgent, extract_grep_citations, extract_citations
from backend.config import settings
from backend.core.context_tracker import context_tracker
from backend.core.event_bus import EventBus
from backend.models.events import EventType, NexusEvent
from backend.services.ollama_client import OllamaClient
from backend.services.shell import run_shell

log = logging.getLogger("nexus.manager")

MAX_FACTS = 30          # cap facts sent to main LLM after relevance filtering
SED_TIMEOUT = 5.0       # seconds per verification command
# Verify more candidates than the cap since 7B will trim them down
VERIFY_CANDIDATES = MAX_FACTS * 5


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
        query: str = "",
    ) -> VerifiedContext:
        # ── Fan-out: all workers in parallel ──────────────────────────────────
        results = list(
            await asyncio.gather(
                *[self._worker.run(t, session_id, codebase_path, settings.worker_timeout) for t in tasks],
                return_exceptions=False,
            )
        )

        for r in results:
            if r.success:
                context_tracker.update_worker(session_id, r.tokens_in, r.tokens_out)

        # ── Collect citations (grep output preferred over SLM extraction) ──────
        all_citations: dict[str, str] = {}
        for result in results:
            if not result.success:
                continue
            for c in extract_grep_citations(result.raw_output):
                all_citations[c] = result.task_id
            for c in extract_citations(result.formatted):
                all_citations.setdefault(c, result.task_id)

        await self.bus.emit(NexusEvent(
            type=EventType.MANAGER_VERIFY,
            session_id=session_id,
            data={"total_citations": len(all_citations)},
        ))

        # ── Step 3: Verify citations with sed (deterministic) ─────────────────
        candidates = list(all_citations.items())[:VERIFY_CANDIDATES]
        verify_results = await asyncio.gather(
            *[self._verify(c, tid, codebase_path, session_id) for c, tid in candidates],
            return_exceptions=True,
        )
        facts: list[VerifiedFact] = [vr for vr in verify_results if isinstance(vr, VerifiedFact)]
        log.info("manager: %d/%d citations verified by sed", len(facts), len(candidates))

        # ── Step 3.5: Relevance filter using qwen2.5:7b ───────────────────────
        if facts and query:
            facts = await self._filter_relevance(query, facts, session_id)

        # ── Step 4: Cap and package ───────────────────────────────────────────
        facts = facts[:MAX_FACTS]

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

    async def _filter_relevance(
        self,
        query: str,
        verified_facts: list[VerifiedFact],
        session_id: str,
    ) -> list[VerifiedFact]:
        """Use qwen2.5:7b to drop verified-but-irrelevant facts before sending to Claude."""

        await self.bus.emit(NexusEvent(
            type=EventType.MANAGER_RELEVANCE_FILTER,
            session_id=session_id,
            data={
                "total_facts": len(verified_facts),
                "model": settings.manager_model,
                "status": "started",
            },
        ))

        # Build compact fact list for the prompt
        facts_text = ""
        for i, fact in enumerate(verified_facts):
            facts_text += f"[{i}] {fact.citation}\n{fact.line_content.strip()[:200]}\n\n"

        prompt = (
            f"You are a relevance filter. Keep citations that could help answer the query.\n\n"
            f"QUERY: {query}\n\n"
            f"CITATIONS:\n{facts_text}\n"
            "Return a JSON array of index numbers to KEEP. Be GENEROUS — only drop citations "
            "that are clearly from a completely different topic (e.g. query is about graphs but "
            "citation is from a string sorting algorithm with no graph connection).\n"
            "When in doubt, KEEP IT. Aim to keep at least 50% of citations.\n"
            "Return ONLY the JSON array. Example: [0,1,2,3,4,5,6,7,8,9]"
        )

        try:
            response, tok_in, tok_out = await self.ollama.complete(
                prompt=prompt,
                model=settings.manager_model,  # qwen2.5:7b
            )
            context_tracker.update_manager(session_id, tok_in, tok_out)
            log.info("relevance filter: tok_in=%d tok_out=%d raw=%r", tok_in, tok_out, response[:200])

            # Extract JSON array from response (model may add surrounding text)
            match = re.search(r'\[[\d,\s]*\]', response)
            if match:
                relevant_indices = json.loads(match.group())
                filtered = [verified_facts[i] for i in relevant_indices if i < len(verified_facts)]
                # Safety floor — never let filter reduce to fewer than 5 facts
                if len(filtered) < 5 and len(verified_facts) >= 5:
                    log.warning("relevance filter returned only %d facts — ignoring, keeping all", len(filtered))
                    filtered = verified_facts

                await self.bus.emit(NexusEvent(
                    type=EventType.MANAGER_RELEVANCE_FILTER,
                    session_id=session_id,
                    data={
                        "total_facts": len(verified_facts),
                        "kept": len(filtered),
                        "dropped": len(verified_facts) - len(filtered),
                        "model": settings.manager_model,
                        "tok_in": tok_in,
                        "tok_out": tok_out,
                        "status": "complete",
                    },
                ))
                log.info("relevance filter: kept=%d dropped=%d", len(filtered), len(verified_facts) - len(filtered))
                return filtered

            else:
                log.warning("relevance filter: could not parse JSON from %r — keeping all", response[:300])
                await self.bus.emit(NexusEvent(
                    type=EventType.MANAGER_RELEVANCE_FILTER,
                    session_id=session_id,
                    data={"status": "parse_failed", "fallback": "keeping_all", "tok_in": tok_in, "tok_out": tok_out},
                ))
                return verified_facts

        except Exception as e:
            log.error("relevance filter FAILED: %s\n%s", e, traceback.format_exc())
            await self.bus.emit(NexusEvent(
                type=EventType.MANAGER_RELEVANCE_FILTER,
                session_id=session_id,
                data={"status": "error", "error": str(e), "fallback": "keeping_all"},
            ))
            # Safe fallback — never crash the pipeline
            return verified_facts

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

        start = max(1, lineno - 1)
        end = lineno + 1
        sed_cmd = f"sed -n '{start},{end}p' \"{rel_path}\""

        try:
            content = (await run_shell(sed_cmd, codebase_path, timeout=SED_TIMEOUT)).strip()
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            log.error("verify FAILED  citation=%s  %s\n%s", citation, reason, traceback.format_exc())
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
        target_idx = lineno - start
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
