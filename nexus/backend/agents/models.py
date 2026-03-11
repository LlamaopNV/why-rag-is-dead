from enum import Enum

from pydantic import BaseModel


class TaskType(str, Enum):
    GREP = "grep"
    CAT = "cat"
    SED = "sed"
    FIND = "find"


class WorkerTask(BaseModel):
    task_id: str
    type: TaskType = TaskType.GREP
    command: str
    description: str


class WorkerResult(BaseModel):
    task_id: str
    success: bool = True
    raw_output: str = ""
    formatted: str = ""
    citations: list[str] = []   # ["path/file.py:42", ...]
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""


class VerifiedFact(BaseModel):
    citation: str           # "path/file.py:42"
    line_content: str       # actual line from sed
    context_lines: str      # ±1 lines for readability
    source_task_id: str


class VerifiedContext(BaseModel):
    facts: list[VerifiedFact] = []

    def to_prompt_string(self) -> str:
        if not self.facts:
            return "No verified context found."

        # Group by file
        by_file: dict[str, list[VerifiedFact]] = {}
        for f in self.facts:
            fname = f.citation.rsplit(":", 1)[0]
            by_file.setdefault(fname, []).append(f)

        parts: list[str] = []
        for fname, facts in by_file.items():
            parts.append(f"=== {fname} ===")
            for fact in sorted(facts, key=lambda x: int(x.citation.rsplit(":", 1)[-1])):
                lineno = fact.citation.rsplit(":", 1)[-1]
                parts.append(f"[line {lineno}] {fact.line_content}")
                if fact.context_lines:
                    parts.append(fact.context_lines)
            parts.append("")

        return "\n".join(parts).strip()

    def token_estimate(self) -> int:
        return len(self.to_prompt_string()) // 4
