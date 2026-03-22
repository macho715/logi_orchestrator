from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def runs_dir(tmp_path: Path) -> Path:
    """Temporary runs directory for tests."""
    d = tmp_path / "runs"
    d.mkdir()
    return d
