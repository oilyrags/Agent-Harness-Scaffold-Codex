from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .security import ensure_within_root


@dataclass(frozen=True)
class Workspace:
    path: Path
    workspace_key: str
    created_now: bool


class WorkspaceManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_for_issue(self, issue_identifier: str) -> Workspace:
        workspace_key = sanitize_workspace_key(issue_identifier)
        path = ensure_within_root(self.root / workspace_key, self.root)
        created_now = not path.exists()
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise NotADirectoryError(path)
        return Workspace(path=path, workspace_key=workspace_key, created_now=created_now)


def sanitize_workspace_key(issue_identifier: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", issue_identifier).strip("._-")
    if not sanitized:
        raise ValueError("issue identifier does not produce a safe workspace key")
    return sanitized
