from __future__ import annotations

from pathlib import Path


class GitWorktreeManager:
    """
    실제 git worktree 생성 대신 폴더만 만든다.
    추후 `git worktree add` 로 교체한다.
    """

    def create_stub(self, base_dir: Path, name: str) -> Path:
        path = base_dir / "worktrees" / name
        path.mkdir(parents=True, exist_ok=True)
        return path
