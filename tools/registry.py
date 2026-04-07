"""
Register LangChain tools for the agent. Add new tools here (plug-and-play).

See docs/tools.md for how to author tools.
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import wraps
from typing import Annotated, Literal

from langchain_core.tools import tool

from agent.permissions import is_safe, request_approval
from MemoryManager.Orchesterator import MemoryOrchestrator
from tools.workspace import resolve_path, search_files as search_files_logic
from tools.mcp_loader import load_mcp_tools
from tools.web_search import search_and_read_web
from tools.shell_executor import run_cli_command


MemoryIntent = Literal[
    "auto",
    "semantic",
    "structured",
    "preferences",
    "schedule",
    "all_stores",
]


def build_tools(orchestrator: MemoryOrchestrator | None = None):
    """
    Build tool callables bound to a MemoryOrchestrator singleton.
    Pass orchestrator for tests; default uses the global singleton.
    """
    orch = orchestrator or MemoryOrchestrator()

    @tool
    def retrieve_user_memory(
        query: Annotated[str, "What to look for in stored memories. Speak naturally, e.g. 'what are my reminders for today?' or 'what is my preferred theme?'"],
        limit: Annotated[int, "Max hits per backend (1–50)."] = 10,
    ) -> str:
        """Load user-specific memories from DesktopLM stores. Call when answering needs past context."""
        return orch.retrieve_for_agent(query, limit)

    @tool
    def get_current_time() -> str:
        """Return the current local date and time (ISO format)."""
        return datetime.now().isoformat(timespec="seconds")

    @tool
    def write_workspace_file(
        filename: Annotated[str, "File name only, e.g. notes.txt"],
        content: Annotated[str, "Full text to write"],
    ) -> str:
        """Create or overwrite a file in the agent workspace sandbox."""
        # Permission check is handled by the callback in trace_callbacks.py
        path = resolve_workspace_file(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return json.dumps({"ok": True, "path": str(path)})

    @tool
    def read_file(
        path: Annotated[str, "Absolute or relative path to the file"],
    ) -> str:
        """Read a text file from the local filesystem."""
        resolved_path = resolve_path(path)
        if not resolved_path.is_file():
            return json.dumps({"ok": False, "error": "file_not_found", "path": str(resolved_path)})
        return resolved_path.read_text(encoding="utf-8")

    @tool
    def search_files(
        search_path: Annotated[str, "Directory to start the search from (e.g., 'Desktop', 'Documents', or a full path)."],
        query: Annotated[str, "The name or partial name of the file or folder to find."],
    ) -> str:
        """
        Searches for files or directories matching a query within a given path.
        This tool can search user's Desktop, Documents, Downloads, or any other directory.
        """
        return search_files_logic(search_path, query)

    # Built-in tools
    all_tools = [
        retrieve_user_memory,
        get_current_time,
        write_workspace_file,
        read_file,
        search_and_read_web,
        run_cli_command,
        search_files,
    ]

    # Load MCP tools from JSON config and wrap as LangChain @tool functions
    mcp_tools_raw = load_mcp_tools()
    for mcp_tool in mcp_tools_raw:
        _mcp = mcp_tool  # capture in closure

        def _make_wrapper(m):
            def _fn(input: Annotated[str, "Input to pass to the MCP tool"] = "") -> str:
                return m(input)
            _fn.__name__ = m.name
            _fn.__doc__ = getattr(m, "description", f"MCP tool: {m.name}")
            return tool(_fn)

        all_tools.append(_make_wrapper(_mcp))

    return all_tools
