import json

from backend.agents.models import TaskType, WorkerTask
from backend.core.context_tracker import context_tracker
from backend.core.event_bus import EventBus
from backend.models.events import EventType, NexusEvent
from backend.services.anthropic_client import AnthropicClient

SYSTEM = """\
You are a query decomposer for a code search system.
Given a user query about a Python codebase, generate 3-5 atomic shell search tasks \
using grep, cat, sed, or find. All commands run from the codebase root directory.

SCOPING RULES — critical for performance:
- Look at the file tree provided. If the query is about a specific domain, scope ALL \
searches to the matching directory. Examples:
    "graph" / "BFS" / "DFS" / "cycle"  →  search in graphs/
    "sort" / "sorting"                  →  search in sorts/
    "tree" / "BST" / "heap"             →  search in data_structures/
    "dynamic programming" / "dp"        →  search in dynamic_programming/
    "string" / "palindrome"             →  search in strings/
- Never search the entire codebase when the query is domain-specific.
- Prefer 3 targeted tasks over 7 broad ones.

COMMAND RULES:
- grep -rn with directory scope (e.g. grep -rn 'pattern' graphs/ --include='*.py')
- find within the scoped directory (e.g. find graphs/ -name '*.py')
- cat specific files only after find/grep identifies them
- Use -l flag to list matching files first, then grep for content

Return ONLY a valid JSON array — no markdown fences, no explanation.
Example:
[
  {"task_id":"t1","type":"grep","command":"grep -rn 'def binary_search' sorts/ --include='*.py'","description":"Find binary search definitions in sorts directory"},
  {"task_id":"t2","type":"find","command":"find sorts/ -name '*binary*' -type f","description":"Locate binary search files"}
]"""


class PlannerAgent:
    def __init__(self, anthropic: AnthropicClient, bus: EventBus):
        self.anthropic = anthropic
        self.bus = bus

    async def plan(self, query: str, session_id: str, file_tree: str) -> list[WorkerTask]:
        await self.bus.emit(NexusEvent(
            type=EventType.PLANNER_START,
            session_id=session_id,
            data={"query": query},
        ))

        # Give planner a sample of the file tree so it can write targeted commands
        file_sample = "\n".join(file_tree.splitlines()[:200])
        user_msg = f"Query: {query}\n\nCurrent codebase files (sample):\n{file_sample}"

        raw, tok_in, tok_out = await self.anthropic.complete(
            messages=[{"role": "user", "content": user_msg}],
            system=SYSTEM,
            max_tokens=1024,
        )

        context_tracker.update_planner(session_id, tok_in, tok_out)
        tasks = _parse_tasks(raw)

        await self.bus.emit(NexusEvent(
            type=EventType.PLANNER_DONE,
            session_id=session_id,
            data={"task_count": len(tasks), "tok_in": tok_in, "tok_out": tok_out},
        ))

        return tasks


def _parse_tasks(raw: str) -> list[WorkerTask]:
    """Parse JSON task list, tolerating minor formatting issues from the model."""
    text = raw.strip()

    # Strip markdown fences if the model added them
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:])
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        data = json.loads(text)
        tasks = []
        for i, t in enumerate(data):
            # Ensure task_id is present
            t.setdefault("task_id", f"t{i+1}")
            tasks.append(WorkerTask(**t))
        return tasks
    except Exception:
        # Fallback: single broad grep so we never return an empty task list
        return [
            WorkerTask(
                task_id="t1",
                type=TaskType.GREP,
                command="grep -rn '' --include='*.py' | head -100",
                description="Fallback broad search",
            )
        ]
