from __future__ import annotations

import json
from pathlib import Path

from app.schemas.job import AuditEvent


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


class AuditService:
    def write(self, path: Path, event: AuditEvent) -> None:
        append_jsonl(path, event.model_dump(mode="json"))
