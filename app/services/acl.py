from __future__ import annotations

from pathlib import Path

import yaml

from app.config import settings


class ACLService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or settings.resolved_config_path
        self._cache: dict[str, list[str]] | None = None

    def load(self) -> dict[str, list[str]]:
        if self._cache is None:
            with self.config_path.open("r", encoding="utf-8") as f:
                self._cache = yaml.safe_load(f) or {}
        return self._cache

    def is_requester(self, username: str) -> bool:
        return username in set(self.load().get("requesters", []))

    def is_approver(self, username: str) -> bool:
        return username in set(self.load().get("approvers", []))

    def is_operator(self, username: str) -> bool:
        return username in set(self.load().get("operators", []))

    def is_repo_allowed(self, repo: str) -> bool:
        return repo in set(self.load().get("repos", []))
