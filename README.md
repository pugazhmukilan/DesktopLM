# DesktopLM

Local-first personal assistant with **hot-swappable LLM providers** (Ollama ↔ Gemini ↔ OpenAI), **LangGraph** for tool use, and **three memory backends** (SQLite, MongoDB, Chroma).

## Quick Start

```bash
git clone https://github.com/your-username/DesktopLM.git
cd DesktopLM
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
desktoplm repl
```

## What you need

1. **Python 3.10+**
2. **[Ollama](https://ollama.com)** running with at least one model pulled (e.g. `ollama pull qwen2.5:7b`)
3. **MongoDB** for preference/fact memories — easiest: `docker compose up -d` from this folder

SQLite and Chroma files live in `MemoryManager/Database/data/` automatically; no extra server needed.

## Configure

Edit the `.env` file in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `DESKTOPLM_LLM_MODE` | `local` | `local` (Ollama), `cloud`, or `auto` (ask at startup) |
| `DESKTOPLM_MODEL` | `qwen2.5:7b` | Ollama model tag |
| `DESKTOPLM_CLOUD_PROVIDER` | `gemini` | Cloud provider: `gemini` or `openai` |
| `DESKTOPLM_CLOUD_MODEL` | `gemini-2.0-flash` | Cloud model name |
| `GOOGLE_API_KEY` | — | Required for Gemini cloud mode |
| `OPENAI_API_KEY` | — | Required for OpenAI cloud mode |
| `DESKTOPLM_MONGO_URI` | `mongodb://127.0.0.1:27017` | MongoDB connection |
| `DESKTOPLM_MONGO_DB` | `memory_db` | MongoDB database name |

## Start Mongo with Docker (optional)

```bash
docker compose up -d
```

## Commands

```bash
desktoplm                    # show usage
desktoplm repl               # interactive chat (recommended)
desktoplm doctor             # verify environment (Ollama, MongoDB, keys, MCP)
desktoplm select-model       # interactive model picker
desktoplm demo-memory        # memory-extract + DB routing demo
desktoplm chat "message"     # single message, then exit
desktoplm "message"          # same as chat (shorthand)
```

### REPL Commands

While inside `desktoplm repl`:

| Command | Description |
|---------|-------------|
| `:switch` | Change LLM model at runtime (local ↔ cloud) |
| `:model` | Show current model info |
| `:tools` | List all loaded tools (built-in + MCP) |
| `:trust <name>` | Trust a tool for this session (skip approval prompts) |
| `:help` | Show commands |
| `:quit` | Exit |

### CLI Flags

| Flag | Description |
|------|-------------|
| `-q`, `--quiet` | Quieter console (errors only) |
| `--yes`, `-y` | Auto-approve all tool actions (skip permission prompts) |

## Tool Permission System

Tools that modify files, execute commands, or call external services require **user approval** before execution:

```
  ⚡ write_workspace_file filename='notes.txt'
  ⚠  Tool 'write_workspace_file' wants to execute:
     Args: filename='notes.txt', content='...'
     Proceed? [Y/n/trust] y
  ✓ (42ms) {"ok": true, "path": "..."}
```

- **Safe tools** (memory retrieval, get time, file reads) run silently
- **Unsafe tools** (file writes, MCP commands) prompt `[Y/n/trust]`
- Type `trust` to whitelist a tool for the current session
- Use `--yes` flag to auto-approve everything

## Adding MCP Tools

Edit `tools/mcp_config.json` to declare external MCP tool servers:

```json
{
  "mcpServers": {
    "my-tool": {
      "command": "uv",
      "args": ["--directory", "/path/to/tool", "run", "main.py"]
    }
  }
}
```

Tools defined here are automatically loaded and available to the LLM. No Python changes needed.

## Data Layout

| Path | Purpose |
|------|---------|
| `MemoryManager/Database/data/sql/memory.db` | SQLite (todos, reminders, constraints) |
| `MemoryManager/Database/data/vectordb/` | Chroma (episodic / semantic) |
| `MemoryManager/Database/data/agent_workspace/` | Sandbox for agent file tools |
| `MemoryManager/Database/data/logs/desktoplm.log` | Rotating trace log |

MongoDB stores documents in the database name from `DESKTOPLM_MONGO_DB`.

## Development

- Adding tools: [docs/tools.md](docs/tools.md)
- `pip install -r requirements.txt` also works

## Uninstall

```bash
pip uninstall desktoplm
```

Your data is **not** removed automatically; delete the data directory if you want a clean wipe.
