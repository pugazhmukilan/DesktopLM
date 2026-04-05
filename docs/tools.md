# DesktopLM tools (plug-and-play)

Tools are **LangChain `@tool` callables** registered in [`tools/registry.py`](../tools/registry.py) and passed to the LangGraph agent in [`agent/graph.py`](../agent/graph.py).

## End-to-end flow

1. **User message** enters [`ChatPipeline.run()`](../agent/pipeline.py).
2. **Write path:** [`MemoryOrchestrator.store_memory_from_prompt()`](../MemoryManager/Orchesterator.py) runs `LocalLLM.memory_extract()` (system prompt in [`LLMS/sys_prompt_slm.py`](../LLMS/sys_prompt_slm.py)) and inserts into SQL / Mongo / Chroma by category.
3. **Read path:** The agent may call **`retrieve_user_memory`**, which maps `intent` + `query` to the right backends inside `MemoryOrchestrator.retrieve_for_agent()` (the model does not choose a database).
4. **Other tools:** time, workspace file read/write (sandbox under `<DESKTOPLM_DATA_DIR>/agent_workspace/`, default `~/.desktoplm/agent_workspace/`).

## How to add a new tool

1. **Implement a pure function** (or small class method) with **typed parameters** and a **string or JSON-serializable return value** suitable for the model context.
2. **Wrap with `@tool`** from `langchain_core.tools` (or `StructuredTool.from_function`).
3. **Append** the tool to the list returned by `build_tools()` in [`tools/registry.py`](../tools/registry.py).
4. If the tool needs **dependencies** (orchestrator, config paths), use a **closure** or `build_tools(orchestrator=...)` pattern like `retrieve_user_memory`.

### Minimal example

```python
from langchain_core.tools import tool
from typing import Annotated

def build_tools(orchestrator=None):
    @tool
    def ping(
        message: Annotated[str, "Echo input"],
    ) -> str:
        """Return a short echo (demo tool)."""
        return f"pong: {message[:200]}"

    return [ping, ...]
```

### Parameter descriptions

Use **`Annotated[type, "docstring"]`** on arguments so the model sees clear JSON-schema descriptions. Prefer **enums / `Literal[...]`** for small fixed sets (see `retrieve_user_memory.intent`).

### Safety

- **Filesystem:** restrict writes to [`AGENT_WORKSPACE`](../agent/config.py) via [`tools/workspace.py`](../tools/workspace.py).
- **Secrets:** do not log full tool arguments in production if they may contain passwords.
- **Mongo / SQL errors:** retrieval methods catch per-store failures and attach them to the JSON returned to the model so the agent can degrade gracefully.

## Memory retrieval intents

| `intent`       | Typical use |
|----------------|-------------|
| `auto`         | Default; mixes vector + schedule SQL + preference Mongo. |
| `semantic`     | Fuzzy / episodic recall (Chroma). |
| `schedule`     | Todos, reminders, commitments, constraints (SQL categories). |
| `preferences`  | Facts and preferences (Mongo categories). |
| `structured`   | Text search across SQL-backed rows. |
| `all_stores`   | Query every backend with smaller per-store limits. |

When unsure, use **`auto`**; document that in the agent system prompt ([`agent/system_prompt.py`](../agent/system_prompt.py)).

## Running the agent

After `pip install -e .` (or `pip install .`), use the **`desktoplm`** command from any directory:

```bash
desktoplm "What is on my schedule this week?"
desktoplm --doctor
```

From a source checkout without installing the entry point:

```bash
python main.py "What is on my schedule this week?"
python -m agent.cli "What do you remember about my preferences?"
```

Memory-only stress demo (no LangGraph):

```bash
python scripts/memory_write_demo.py
```

## Dependencies

See [`requirements.txt`](../requirements.txt): `langgraph`, `langchain`, `langchain-ollama`, `ollama`, DB drivers, etc.
