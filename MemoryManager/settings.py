"""
Paths and external service settings. Each user/machine gets their own data under
DESKTOPLM_DATA_DIR (default: ~/.desktoplm on all platforms).
"""

from __future__ import annotations

import os
from pathlib import Path

import dotenv

_dotenv_loaded = False


def _ensure_dotenv() -> None:
    global _dotenv_loaded
    if not _dotenv_loaded:
        dotenv.load_dotenv()
        _dotenv_loaded = True


def get_data_dir() -> Path:
    """Root directory for SQLite, Chroma, agent workspace, etc."""
    _ensure_dotenv()
    raw = os.getenv("DESKTOPLM_DATA_DIR", "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
    else:
        # Default to MemoryManager/Database/data relative to this file
        p = (Path(__file__).resolve().parent / "Database" / "data").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def sqlite_db_path() -> str:
    d = get_data_dir() / "sql"
    d.mkdir(parents=True, exist_ok=True)
    return str(d / "memory.db")


def chroma_persist_path() -> str:
    d = get_data_dir() / "vectordb"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def agent_workspace_path() -> Path:
    d = get_data_dir() / "agent_workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def mongo_uri() -> str:
    _ensure_dotenv()
    return os.getenv("DESKTOPLM_MONGO_URI", "mongodb://127.0.0.1:27017")


def mongo_db_name() -> str:
    _ensure_dotenv()
    return os.getenv("DESKTOPLM_MONGO_DB", "memory_db")
