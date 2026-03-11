import logging
import traceback
from pathlib import Path
from typing import Optional

log = logging.getLogger("nexus.orchestrator")

from backend.agents.manager import ManagerAgent
from backend.agents.planner import PlannerAgent
from backend.config import settings
from backend.core.context_tracker import context_tracker
from backend.core.event_bus import event_bus
from backend.models.events import EventType, NexusEvent
from backend.services.anthropic_client import AnthropicClient
from backend.services.indexer import indexer
from backend.services.ollama_client import OllamaClient

# Words to skip when extracting query keywords for naive file search
_STOP = {
    "the","a","an","is","it","in","of","to","and","or","how","does",
    "what","which","where","find","show","me","all","any","with","for",
    "are","was","were","be","been","have","has","had","do","did","not",
    "this","that","these","those","their","there","they","from","use",
    "used","using","can","could","would","should","will","way",
}

MAIN_SYSTEM = (
    "You are an expert code analyst. "
    "You have been given verified, cited excerpts from a Python codebase. "
    "Every citation was independently verified by running shell commands on the actual files. "
    "Answer the user's question using ONLY the provided context. "
    "Cite sources as [file.py:line]. "
    "If the context is insufficient, say so explicitly."
)

# Naive mode: sample up to this many chars from actual files for token counting
NAIVE_CHAR_BUDGET = 150_000   # ~37K tokens — representative sample
NAIVE_FILE_LIMIT = 200


class Orchestrator:
    def __init__(self):
        self._anthropic = AnthropicClient()
        self._ollama = OllamaClient()
        self._planner = PlannerAgent(self._anthropic, event_bus)
        self._manager = ManagerAgent(self._ollama, event_bus)

    async def run(
        self,
        query: str,
        session_id: str,
        codebase_path: Optional[str] = None,
        naive_mode: bool = True,
    ):
        try:
            cb_path = Path(codebase_path) if codebase_path else indexer.codebase_path
            if not cb_path or not cb_path.exists():
                await event_bus.emit(NexusEvent(
                    type=EventType.ERROR,
                    session_id=session_id,
                    data={"error": "No codebase indexed. POST /api/index first."},
                ))
                return

            # Start with 0 — naive estimate is computed honestly at the end
            # via keyword-matched file sampling, not a full-codebase extrapolation
            context_tracker.set_naive_estimate(session_id, 0)

            # ── 1. Planner ────────────────────────────────────────────────────
            tasks = await self._planner.plan(query, session_id, indexer.get_file_tree())

            # ── 2. Manager → verified context ─────────────────────────────────
            verified = await self._manager.run(tasks, session_id, cb_path)

            # Token snapshot after workers + manager
            await _emit_token_update(session_id)

            # ── 3. Main LLM (streaming) ───────────────────────────────────────
            await event_bus.emit(NexusEvent(
                type=EventType.MAIN_LLM_START,
                session_id=session_id,
                data={
                    "context_facts": len(verified.facts),
                    "context_tokens": verified.token_estimate(),
                },
            ))

            messages = [{
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    "=== Verified Codebase Context ===\n"
                    f"{verified.to_prompt_string()}"
                ),
            }]

            full_response: list[str] = []
            async for chunk, tok_in, tok_out in self._anthropic.stream(
                messages=messages,
                system=MAIN_SYSTEM,
            ):
                if tok_in is not None:
                    # Final sentinel — stream ended
                    context_tracker.update_main(session_id, tok_in, tok_out)
                    await event_bus.emit(NexusEvent(
                        type=EventType.MAIN_LLM_DONE,
                        session_id=session_id,
                        data={
                            "response": "".join(full_response),
                            "tokens": context_tracker.get(session_id).model_dump(),
                        },
                    ))
                else:
                    full_response.append(chunk)
                    await event_bus.emit(NexusEvent(
                        type=EventType.MAIN_LLM_STREAM,
                        session_id=session_id,
                        data={"chunk": chunk},
                    ))

            # ── 4. Naive comparison ────────────────────────────────────────────
            if naive_mode and indexer.indexed:
                await self._run_naive(session_id, query)

            # ── Done ──────────────────────────────────────────────────────────
            final = context_tracker.get(session_id)
            await event_bus.emit(NexusEvent(
                type=EventType.SESSION_DONE,
                session_id=session_id,
                data={
                    "tokens": final.model_dump(),
                    "nexus_total": final.total_nexus,
                    "naive_estimate": final.naive_estimate,
                    "reduction_pct": final.reduction_pct,
                },
            ))

        except Exception as e:
            await event_bus.emit(NexusEvent(
                type=EventType.ERROR,
                session_id=session_id,
                data={"error": str(e), "trace": traceback.format_exc()},
            ))

    async def _run_naive(self, session_id: str, query: str):
        """
        Honest naive estimate: what it would cost to answer this query without NEXUS.

        Simulates a developer who greps for relevant files and dumps them into Claude.
        Uses count_tokens (no LLM call cost). Falls back to char-based estimate if
        the API call fails, so the UI always shows a real number.
        """
        if not indexer.codebase_path:
            log.warning("naive: no codebase path, skipping")
            return

        # Extract meaningful keywords from the query
        keywords = [
            w.lower() for w in query.replace("?", " ").replace(",", " ").split()
            if len(w) > 3 and w.lower() not in _STOP
        ][:6]

        log.info("naive: keywords=%s", keywords)
        if not keywords:
            log.warning("naive: no keywords extracted from query")
            return

        # Scan indexed files in Python to find keyword matches
        relevant: list[str] = []
        for rel_path in indexer.get_file_list():
            abs_path = indexer.safe_path(rel_path)
            if not abs_path:
                continue
            if indexer.file_index[rel_path]["size"] > 200_000:
                continue
            try:
                text = abs_path.read_text(encoding="utf-8", errors="ignore").lower()
                if any(kw in text for kw in keywords):
                    relevant.append(rel_path)
                    if len(relevant) >= 40:
                        break
            except Exception:
                continue

        log.info("naive: %d relevant files found", len(relevant))
        if not relevant:
            log.warning("naive: no files matched keywords, falling back to char estimate")
            # Fallback: estimate from a sample of all files
            relevant = indexer.get_file_list()[:20]

        # Build the naive context dump
        parts: list[str] = []
        total_chars = 0
        char_cap = 200_000

        for rel_path in relevant:
            abs_path = indexer.safe_path(rel_path)
            if not abs_path:
                continue
            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                chunk = f"=== {rel_path} ===\n{content}\n"
                if total_chars + len(chunk) > char_cap:
                    break
                parts.append(chunk)
                total_chars += len(chunk)
            except Exception:
                continue

        if not parts:
            log.warning("naive: could not build context dump")
            return

        log.info("naive: built dump from %d files, %d chars", len(parts), total_chars)

        # Use main_out as proxy for naive output tokens — Claude would write a
        # similar-length response either way, so this makes the comparison fair.
        # naive_total = what you'd send (input) + what Claude would respond (output)
        main_out = context_tracker.get(session_id).main_out

        # Char-based fallback (always available, no API call)
        char_based = (total_chars // 4) + main_out
        context_tracker.set_naive_estimate(session_id, char_based)
        await _emit_token_update(session_id)

        # Exact count from Anthropic's count_tokens endpoint (no LLM cost)
        messages = [{"role": "user", "content": f"{''.join(parts)}\n\nQuestion: {query}"}]
        try:
            naive_input = await self._anthropic.count_tokens(messages=messages)
            naive_total = naive_input + main_out   # input + output = total
            log.info(
                "naive: input=%d  output_proxy=%d  total=%d  char_estimate=%d",
                naive_input, main_out, naive_total, char_based,
            )
            context_tracker.set_naive_estimate(session_id, naive_total)
            await _emit_token_update(session_id, naive_file_count=len(parts))
        except Exception as e:
            log.warning("naive: count_tokens failed (%s), using char estimate %d", e, char_based)
            # char_based already set above — nothing more to do


async def _emit_token_update(session_id: str, **extra):
    stats = context_tracker.get(session_id)
    await event_bus.emit(NexusEvent(
        type=EventType.TOKEN_UPDATE,
        session_id=session_id,
        data={**stats.model_dump(), **extra},
    ))


# Singleton
orchestrator = Orchestrator()
