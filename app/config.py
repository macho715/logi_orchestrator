from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "hvdc-orchestrator"))
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "dev"))
    timezone: str = field(default_factory=lambda: os.getenv("APP_TIMEZONE", "Asia/Dubai"))
    base_dir: Path = field(default_factory=lambda: Path(os.getenv("APP_BASE_DIR", ".")).resolve())
    config_path: Path = field(default_factory=lambda: Path(os.getenv("APP_CONFIG_PATH", "config/acl.yaml")))
    runs_dir: Path = field(default_factory=lambda: Path(os.getenv("APP_RUNS_DIR", "ops/orchestrator/runs")))
    reports_dir: Path = field(default_factory=lambda: Path(os.getenv("APP_REPORTS_DIR", "ops/orchestrator/reports")))
    audit_dir: Path = field(default_factory=lambda: Path(os.getenv("APP_AUDIT_DIR", "ops/orchestrator/audit")))
    default_repo: str = field(default_factory=lambda: os.getenv("APP_DEFAULT_REPO", "macho715/logi_hvdc_dash"))

    def resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else (self.base_dir / path).resolve()

    @property
    def resolved_config_path(self) -> Path:
        return self.resolve(self.config_path)

    @property
    def resolved_runs_dir(self) -> Path:
        return self.resolve(self.runs_dir)

    @property
    def resolved_reports_dir(self) -> Path:
        return self.resolve(self.reports_dir)

    @property
    def resolved_audit_dir(self) -> Path:
        return self.resolve(self.audit_dir)


settings = Settings()
