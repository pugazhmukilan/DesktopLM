"""
Tool permission system for DesktopLM.

Tools tagged as unsafe require user approval before execution.
Read-only tools (memory retrieval, get time) execute silently.
"""

from __future__ import annotations

import sys
from typing import Any, Callable

# Tools that are always safe (no approval needed)
SAFE_TOOLS: set[str] = {
    "retrieve_user_memory",
    "get_current_time",
    "read_file",
    "search_and_read_web",
    "search_files",
}

# Session-level whitelist (user can :trust a tool)
_session_trusted: set[str] = set()

# Global auto-approve flag (set via --yes CLI flag)
_auto_approve: bool = False


def set_auto_approve(val: bool) -> None:
    global _auto_approve
    _auto_approve = val


def trust_tool(name: str) -> None:
    """Whitelist a tool for the current session."""
    _session_trusted.add(name)


def is_safe(tool_name: str) -> bool:
    """Check if a tool can run without user approval."""
    if _auto_approve:
        return True
    if tool_name in SAFE_TOOLS:
        return True
    if tool_name in _session_trusted:
        return True
    return False


def request_approval(tool_name: str, arguments: dict[str, Any]) -> bool:
    """Prompt the user for approval to run an unsafe tool.

    Returns True if approved, False if denied.
    """
    if is_safe(tool_name):
        return True

    # Format arguments compactly
    args_preview = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    if len(args_preview) > 120:
        args_preview = args_preview[:117] + "..."

    print(f"\n  [!] Tool '{tool_name}' wants to execute:", flush=True)
    print(f"      Args: {args_preview}", flush=True)

    try:
        answer = input("      Proceed? [Y/n/trust] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n      Denied.")
        return False

    if answer in ("trust", "t"):
        trust_tool(tool_name)
        print(f"      [ok] Trusted '{tool_name}' for this session.")
        return True

    if answer in ("", "y", "yes"):
        return True

    print("      [X] Denied.")
    return False
