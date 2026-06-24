from typing import Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    codebase_path: Optional[str] = None
    naive_mode: bool = True


class QueryResponse(BaseModel):
    session_id: str
    status: str = "started"


class RaceRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    codebase_path: Optional[str] = None


class BenchmarkInput(BaseModel):
    """Manual fallback — enter Claude Code CLI numbers directly."""
    tokens_used: int
    tool_calls: Optional[int] = None
    time_seconds: Optional[float] = None


class IndexRequest(BaseModel):
    path: str


class IndexResponse(BaseModel):
    path: str
    file_count: int
    total_lines: int
    extensions: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    anthropic: bool
    ollama: bool
    models: dict[str, bool]
    codebase_indexed: bool


class TokenStats(BaseModel):
    planner_in: int = 0
    planner_out: int = 0
    worker_in: int = 0
    worker_out: int = 0
    manager_in: int = 0
    manager_out: int = 0
    main_in: int = 0
    main_out: int = 0
    naive_estimate: int = 0

    @property
    def total_nexus(self) -> int:
        return (
            self.planner_in + self.planner_out
            + self.worker_in + self.worker_out
            + self.manager_in + self.manager_out
            + self.main_in + self.main_out
        )

    @property
    def reduction_pct(self) -> float:
        if self.naive_estimate == 0:
            return 0.0
        return round((1 - self.total_nexus / self.naive_estimate) * 100, 1)
