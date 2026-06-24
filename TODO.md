# TODO

- [ ] Remember to thank Chris, Olivier and Sandeep for this amazing workflow.

## Setup follow-ups noticed at bootstrap

- [ ] No backend test runner installed. `pytest` is referenced via `.pytest_cache/` in `.gitignore` but is not in `nexus/requirements.txt`. Add `pytest` (and `pytest-asyncio` for the async pipeline), create `nexus/backend/tests/`, and wire a `test` command so the pre-commit gate has something to run.
- [ ] No linter or formatter configured for the backend. Pick one (for example `ruff`) and add a lint command.
- [ ] No frontend test runner configured. Add one (for example `vitest`) if frontend logic grows.
- [ ] No CI configured. Once test and lint commands exist, add a CI workflow that runs them against `staging`.
- [ ] Phase 4 (Polish) not started: E2E tests, side-by-side comparison, provenance display.
