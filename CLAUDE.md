# CLAUDE.md

- logi-orchestrator stub v1.
- Commands: `uvicorn app.main:app --reload --port 8000`, `pytest`, `ruff check app tests`, `ruff format --check app tests`, `mypy app`.
- Gate bypass is forbidden: no write before plan approval, no completion before merge approval.
- Preserve `JobState`, `JobEvent`, `transition()`, and Telegram command contracts.
- Treat `retry`, outbound Telegram, real Claude/Codex execution, real `git worktree add`, and real merge as unimplemented.
- If commands, states, ACL, or artifact paths change, update code, tests, README, and ops docs together.
- One writer = one worktree.
- Never write secrets or PII to logs or artifacts.
- Keep routes thin, put logic in services, and do not report completion until relevant tests pass.
