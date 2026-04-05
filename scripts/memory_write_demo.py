"""
Memory-only demo. Prefer: desktoplm demo-memory
"""

from __future__ import annotations

import sys

from agent.demos import run_memory_write_demo

if __name__ == "__main__":
    raise SystemExit(run_memory_write_demo())
