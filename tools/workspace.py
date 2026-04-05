"""Sandbox paths for file tools (agent cannot escape this directory)."""

from __future__ import annotations

import re
from pathlib import Path

from MemoryManager.settings import agent_workspace_path

_SAFE_NAME = re.compile(r"^[\w.\- ]{1,200}$")


def get_agent_workspace() -> Path:
    return agent_workspace_path()


# Resolved at import for tools that read this constant
AGENT_WORKSPACE = agent_workspace_path()


def resolve_workspace_file(filename: str) -> Path:
    """
    Map a simple filename to a path under the per-user agent workspace.
    Rejects path components and traversal.
    """
    root = agent_workspace_path()
    name = Path(filename).name
    if not name or name != filename.strip():
        raise ValueError("Use a plain file name (no paths).")
    if not _SAFE_NAME.match(name):
        raise ValueError("Invalid file name; use letters, numbers, ._- and spaces only.")
    path = (root / name).resolve()
    root_resolved = root.resolve()
    if root_resolved != path and root_resolved not in path.parents:
        raise ValueError("Path must stay inside the agent workspace.")
    return path
