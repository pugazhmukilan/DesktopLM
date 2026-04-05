"""Central configuration for the agent (chat model, limits, cloud settings)."""

from __future__ import annotations

import os
from pathlib import Path

import dotenv

from MemoryManager.settings import agent_workspace_path, get_data_dir

dotenv.load_dotenv()

# Per-user data root (SQLite, Chroma, workspace, etc.)
DATA_DIR: Path = get_data_dir()
AGENT_WORKSPACE: Path = agent_workspace_path()
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Local model (Ollama)
CHAT_MODEL = os.getenv("DESKTOPLM_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST") or None

# LLM mode: "local" (default), "cloud", "auto" (ask at startup)
LLM_MODE = os.getenv("DESKTOPLM_LLM_MODE", "local").strip().lower()

# Cloud provider settings
CLOUD_PROVIDER = os.getenv("DESKTOPLM_CLOUD_PROVIDER", "gemini").strip().lower()
CLOUD_MODEL = os.getenv("DESKTOPLM_CLOUD_MODEL", "gemini-2.0-flash").strip()

MAX_TOOL_RESPONSE_CHARS = int(os.getenv("DESKTOPLM_MAX_TOOL_CHARS", "12000"))

__all__ = [
    "DATA_DIR",
    "AGENT_WORKSPACE",
    "PROJECT_ROOT",
    "CHAT_MODEL",
    "OLLAMA_BASE_URL",
    "LLM_MODE",
    "CLOUD_PROVIDER",
    "CLOUD_MODEL",
    "MAX_TOOL_RESPONSE_CHARS",
]
