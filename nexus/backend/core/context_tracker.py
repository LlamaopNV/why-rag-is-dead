from backend.models.schemas import TokenStats


class ContextTracker:
    def __init__(self):
        self._sessions: dict[str, TokenStats] = {}

    def get(self, session_id: str) -> TokenStats:
        if session_id not in self._sessions:
            self._sessions[session_id] = TokenStats()
        return self._sessions[session_id]

    def update_planner(self, session_id: str, in_t: int, out_t: int):
        s = self.get(session_id)
        s.planner_in += in_t
        s.planner_out += out_t

    def update_worker(self, session_id: str, in_t: int, out_t: int):
        s = self.get(session_id)
        s.worker_in += in_t
        s.worker_out += out_t

    def update_manager(self, session_id: str, in_t: int, out_t: int):
        s = self.get(session_id)
        s.manager_in += in_t
        s.manager_out += out_t

    def update_main(self, session_id: str, in_t: int, out_t: int):
        s = self.get(session_id)
        s.main_in += in_t
        s.main_out += out_t

    def set_naive_estimate(self, session_id: str, tokens: int):
        self.get(session_id).naive_estimate = tokens

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)


# Singleton
context_tracker = ContextTracker()
