#!/usr/bin/env python3
"""Thin wrapper: same as `desktoplm` when run from a repo clone."""

from __future__ import annotations

import sys

from agent.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
