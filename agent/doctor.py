"""Lightweight environment checks for a fresh install."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

from MemoryManager.settings import get_data_dir, mongo_db_name, mongo_uri

# ANSI helpers
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def run_doctor() -> int:
    try:
        from agent.run_logging import configure_logging
        configure_logging()
    except ImportError:
        pass

    ok = True
    print(f"\n{_BOLD}DesktopLM -- Environment Check{_RESET}\n")

    # -- Data directory --
    try:
        d = get_data_dir()
        print(f"  {_GREEN}[ok]{_RESET} Data directory: {d}")
    except Exception as e:
        ok = False
        print(f"  {_RED}[FAIL]{_RESET} Data directory: {e}")

    # -- Ollama --
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print(f"  {_GREEN}[ok]{_RESET} Ollama reachable at http://127.0.0.1:11434")
                import json
                data = json.loads(resp.read())
                models = data.get("models", [])
                if models:
                    print(f"    {_DIM}Available models:{_RESET}")
                    for m in models:
                        name = m.get("name", "?")
                        size = m.get("size", 0)
                        gb = f"{size / (1024**3):.1f} GB" if size > 0 else "?"
                        print(f"      - {name} ({gb})")
                else:
                    print(f"    {_YELLOW}[!]{_RESET} No models pulled. Run: ollama pull qwen2.5:7b")
            else:
                ok = False
                print(f"  {_RED}[FAIL]{_RESET} Ollama returned HTTP {resp.status}")
    except Exception as e:
        ok = False
        print(f"  {_RED}[FAIL]{_RESET} Ollama: {e}")
        print(f"    Install from https://ollama.com and run `ollama serve`.")

    # -- MongoDB --
    uri = mongo_uri()
    dbn = mongo_db_name()
    try:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        client.close()
        print(f"  {_GREEN}[ok]{_RESET} MongoDB: {uri} (db: {dbn})")
    except Exception as e:
        ok = False
        print(f"  {_RED}[FAIL]{_RESET} MongoDB ({uri}): {e}")
        print(f"    Run: docker compose up -d  or install MongoDB locally.")

    # -- Cloud API keys --
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if google_key:
        masked = google_key[:8] + "..." + google_key[-4:]
        print(f"  {_GREEN}[ok]{_RESET} GOOGLE_API_KEY: {_DIM}{masked}{_RESET}")
    else:
        print(f"  {_DIM}[ ]{_RESET} GOOGLE_API_KEY: not set (optional, needed for Gemini cloud mode)")

    if openai_key:
        masked = openai_key[:8] + "..." + openai_key[-4:]
        print(f"  {_GREEN}[ok]{_RESET} OPENAI_API_KEY: {_DIM}{masked}{_RESET}")
    else:
        print(f"  {_DIM}[ ]{_RESET} OPENAI_API_KEY: not set (optional, needed for OpenAI cloud mode)")

    # -- MCP config --
    from pathlib import Path
    mcp_config = Path(__file__).resolve().parents[1] / "tools" / "mcp_config.json"
    if mcp_config.is_file():
        try:
            import json
            cfg = json.loads(mcp_config.read_text(encoding="utf-8"))
            n = len(cfg.get("mcpServers", {}))
            print(f"  {_GREEN}[ok]{_RESET} MCP config: {n} server(s) defined")
        except Exception as e:
            print(f"  {_YELLOW}[!]{_RESET} MCP config exists but invalid: {e}")
    else:
        print(f"  {_DIM}[ ]{_RESET} MCP config: not found (tools/mcp_config.json)")

    # -- Summary --
    print()
    if ok:
        print(f"  {_GREEN}All checks passed.{_RESET} Try: desktoplm repl")
    else:
        print(f"  {_YELLOW}Fix the items above, then run again.{_RESET}")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run_doctor())
