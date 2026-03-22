from __future__ import annotations

import pytest


@pytest.fixture()
def runs_dir(tmp_path):
    """Temporary runs directory for tests."""
    d = tmp_path / "runs"
    d.mkdir()
    return d
