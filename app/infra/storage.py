from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.core.exceptions import NotFoundError
from app.schemas.job import JobRecord


class FileJobStore:
    def __init__(self, runs_dir: Path | None = None) -> None:
        self.runs_dir = runs_dir or settings.resolved_runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        return self.runs_dir / job_id

    def job_file(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def audit_file(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "audit" / "events.jsonl"

    def create(self, record: JobRecord) -> JobRecord:
        job_dir = self.job_dir(record.job_id)
        (job_dir / "plan").mkdir(parents=True, exist_ok=True)
        (job_dir / "review").mkdir(parents=True, exist_ok=True)
        (job_dir / "codex").mkdir(parents=True, exist_ok=True)
        (job_dir / "tests").mkdir(parents=True, exist_ok=True)
        (job_dir / "audit").mkdir(parents=True, exist_ok=True)
        self.save(record)
        return record

    def save(self, record: JobRecord) -> JobRecord:
        path = self.job_file(record.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = record.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return record

    def get(self, job_id: str) -> JobRecord:
        path = self.job_file(job_id)
        if not path.exists():
            raise NotFoundError(f"존재하지 않는 job_id 입니다: {job_id}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return JobRecord.model_validate(data)

    def list_artifacts(self, job_id: str) -> list[str]:
        record = self.get(job_id)
        return record.artifacts
