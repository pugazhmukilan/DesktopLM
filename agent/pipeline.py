"""End-to-end user turn: persist memory, then run the tool-calling agent."""

from __future__ import annotations

import logging
import os

from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import build_agent_graph
from agent.trace_callbacks import DesktopLMTraceCallback
from agent.permissions import trust_tool, set_auto_approve
from LLMS.provider import LLMProvider
from LLMS.model_selector import select_model_interactive
from MemoryManager.Orchesterator import MemoryOrchestrator
from LLMS.provider import get_llm_provider
from tools.registry import build_tools
from tools.workspace import resolve_path

logger = logging.getLogger("desktoplm.pipeline")

# ANSI helpers (ASCII-safe)
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_MAGENTA = "\033[35m"
_BLUE = "\033[94m"
_RESET = "\033[0m"


def _message_content_str(message) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content or "")


def _last_assistant_text(messages: list) -> str:
    """Best-effort final user-visible reply after a graph turn."""
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            text = _message_content_str(m).strip()
            if text:
                return _message_content_str(m)
    return ""


class ChatPipeline:
    """
    Connects memory write path (orchestrator) with the chat agent (LangGraph).
    Supports hot-swapping the LLM provider at runtime.
    """

    def __init__(self, orchestrator: MemoryOrchestrator | None = None):
        self._provider = LLMProvider()
        self._orchestrator = orchestrator or MemoryOrchestrator()
        self._graph = build_agent_graph(self._orchestrator, self._provider)

    def _rebuild_graph(self):
        """Rebuild the LangGraph after a model switch."""
        self._graph = build_agent_graph(self._orchestrator, self._provider)

    def _invoke_agent(self, messages: list) -> dict:
        """LangGraph invoke with trace logging and terminal tool lines."""
        cb = DesktopLMTraceCallback()
        logger.debug("Agent graph invoke message_count=%s", len(messages))
        return self._graph.invoke({"messages": messages}, config={"callbacks": [cb]})

    def run(self, user_message: str) -> str:
        if not (user_message or "").strip():
            return ""

        logger.info("Turn start (memory extract + route + agent)")
        self._orchestrator.store_memory_from_prompt(user_message)

        result = self._invoke_agent([HumanMessage(content=user_message.strip())])
        messages = result.get("messages") or []
        reply = _last_assistant_text(messages)
        logger.info("Turn end; assistant reply length=%s", len(reply))
        return reply

    def _print_header(self):
        """Print the session header with model info."""
        info = self._provider.current_info()
        mode_label = "local/Ollama" if info["mode"] == "local" else f"cloud/{info['provider']}"

        from tools.registry import build_tools
        from tools.mcp_loader import load_mcp_tools
        mcp_count = len(load_mcp_tools())
        tool_count = len(build_tools(self._orchestrator))

        print()
        print(f"+{'=' * 50}+")
        print(f"|{_BOLD}  DesktopLM{_RESET}{' ' * 40}|")
        print(f"|  Model: {_CYAN}{info['model']}{_RESET} ({mode_label})")
        print(f"|  Tools: {tool_count} loaded ({mcp_count} MCP)")
        print(f"+{'=' * 50}+")
        print()
        print(f"  {_DIM}Commands: :switch  :model  :tools  :trust <name>  :help  :quit{_RESET}")
        print()

    def _handle_repl_command(self, line: str, messages: list) -> bool:
        """Handle REPL colon-commands.  Returns True if the command was handled."""
        cmd = line.lower().strip()

        if cmd in (":quit", ":q", ":exit"):
            print(f"\n{_DIM}Bye.{_RESET}")
            raise SystemExit(0)

        if cmd == ":help":
            print(f"""
  {_BOLD}REPL Commands{_RESET}
  :switch          Switch LLM model (local <-> cloud)
  :model           Show current model info
  :tools           List loaded tools
  :trust <name>    Trust a tool for this session (skip approval)
  :help            Show this help
  :quit            Exit
""")
            return True

        if cmd == ":model":
            info = self._provider.current_info()
            mode_label = "local/Ollama" if info["mode"] == "local" else f"cloud/{info['provider']}"
            print(f"\n  {_CYAN}{info['model']}{_RESET} ({mode_label})\n")
            return True

        if cmd == ":tools":
            from tools.registry import build_tools
            from tools.mcp_loader import load_mcp_tools
            all_t = build_tools(self._orchestrator)
            mcp_t = load_mcp_tools()
            mcp_names = {t.name for t in mcp_t}
            print(f"\n  {_BOLD}Loaded Tools ({len(all_t)}):{_RESET}")
            for t in all_t:
                name = getattr(t, "name", "?")
                desc = getattr(t, "description", "")[:60]
                tag = f" {_YELLOW}[MCP]{_RESET}" if name in mcp_names else ""
                from agent.permissions import is_safe as _is_safe
                safety = f"{_GREEN}safe{_RESET}" if _is_safe(name) else f"{_YELLOW}approval{_RESET}"
                print(f"    - {name}{tag}  ({safety})  {_DIM}{desc}{_RESET}")
            print()
            return True

        if cmd == ":switch":
            selection = select_model_interactive()
            if selection["mode"] == "local":
                self._provider.switch_to_local(selection["model"])
            else:
                self._provider.switch_to_cloud(
                    selection["provider"],
                    selection["model"],
                    selection.get("api_key", ""),
                )
            self._rebuild_graph()
            info = self._provider.current_info()
            mode_label = "local/Ollama" if info["mode"] == "local" else f"cloud/{info['provider']}"
            print(f"\n  {_GREEN}[ok]{_RESET} Switched to {_CYAN}{info['model']}{_RESET} ({mode_label})\n")
            return True

        if cmd.startswith(":trust "):
            name = cmd[7:].strip()
            if name:
                trust_tool(name)
                print(f"\n  {_GREEN}[ok]{_RESET} Trusted '{name}' for this session.\n")
            return True

        return False

    def run_repl(self) -> int:
        """Interactive session -- same store init, LangGraph keeps full message history."""
        self._print_header()
        messages: list = []

        while True:
            try:
                line = input(f"{_BOLD}{_BLUE}You>{_RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{_DIM}Bye.{_RESET}")
                return 0

            if not line:
                continue

            if line.lower() in ("exit", "quit"):
                print(f"{_DIM}Bye.{_RESET}")
                return 0

            # Handle colon-commands
            if line.startswith(":"):
                if self._handle_repl_command(line, messages):
                    continue

            logger.info("REPL turn start user_len=%s", len(line))
            self._orchestrator.store_memory_from_prompt(line)

            messages.append(HumanMessage(content=line))
            result = self._invoke_agent(messages)
            messages = list(result.get("messages") or messages)

            reply = _last_assistant_text(messages)
            logger.info("REPL turn end reply_len=%s", len(reply))
            print(f"\n{_BOLD}{_GREEN}Assistant>{_RESET} {reply}\n")
