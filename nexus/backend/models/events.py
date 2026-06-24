import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator


class EventType(str, Enum):
    # Planner
    PLANNER_START = "planner.start"
    PLANNER_DONE = "planner.done"

    # Worker
    WORKER_SPAWN = "worker.spawn"
    WORKER_COMMAND = "worker.command"
    WORKER_RESULT = "worker.result"
    WORKER_FAILED = "worker.failed"
    WORKER_TIMEOUT = "worker.timeout"
    WORKER_KILLED = "worker.killed"

    # Manager
    MANAGER_VERIFY = "manager.verify"
    MANAGER_VERIFY_OK = "manager.verify_ok"
    MANAGER_VERIFY_FAIL = "manager.verify_fail"
    MANAGER_RELEVANCE_FILTER = "manager.relevance_filter"
    MANAGER_PACKAGE = "manager.package"

    # Main LLM
    MAIN_LLM_START = "main_llm.start"
    MAIN_LLM_STREAM = "main_llm.stream"
    MAIN_LLM_DONE = "main_llm.done"

    # Token tracking
    TOKEN_UPDATE = "token.update"

    # Benchmark (Claude Code CLI race)
    BENCHMARK_STARTED  = "benchmark.started"
    BENCHMARK_PROGRESS = "benchmark.progress"
    BENCHMARK_STREAM   = "benchmark.stream"
    BENCHMARK_COMPLETE = "benchmark.complete"
    BENCHMARK_TIMEOUT  = "benchmark.timeout"
    BENCHMARK_ERROR    = "benchmark.error"

    # System
    ERROR = "system.error"
    SESSION_DONE = "session.done"


class NexusEvent(BaseModel):
    type: EventType
    session_id: str
    timestamp: float = 0.0
    data: dict[str, Any] = {}

    @model_validator(mode="after")
    def set_timestamp(self) -> "NexusEvent":
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        return self
