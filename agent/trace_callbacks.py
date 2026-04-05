"""
LangChain / LangGraph callbacks: rich formatted terminal output for tools,
permission prompts, and full detail logging to file.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from agent.permissions import is_safe, request_approval

_log = logging.getLogger("desktoplm.trace")

# ANSI color helpers (ASCII-safe for Windows cp1252)
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_MAGENTA = "\033[35m"
_RESET = "\033[0m"


def _safe_json(obj: Any, max_len: int = 50000) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str, indent=2)
    except (TypeError, ValueError):
        s = repr(obj)
    if len(s) > max_len:
        return s[: max_len - 40] + "\n... [truncated]"
    return s


def _messages_preview(messages: list[list[BaseMessage]]) -> str:
    out = []
    for batch in messages:
        for m in batch:
            role = getattr(m, "type", m.__class__.__name__)
            content = getattr(m, "content", "")
            if isinstance(content, list):
                content = _safe_json(content, 8000)
            else:
                content = str(content)[:8000]
            out.append(f"  [{role}] {content[:4000]}{'...' if len(content) > 4000 else ''}")
    return "\n".join(out) if out else "(empty)"


class DesktopLMTraceCallback(BaseCallbackHandler):
    """Professional CLI output: verbose tool logging, permission prompts, spinner hints."""

    def __init__(self):
        super().__init__()
        self._tool_start_times: dict[UUID, float] = {}
        self._denied_runs: set[UUID] = set()

    # ---- LLM events ----

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        _log.info(
            "LLM_CHAT_START run_id=%s serialized=%s\nmessages:\n%s\nkwargs=%s",
            run_id,
            _safe_json(serialized, 8000),
            _messages_preview(messages),
            _safe_json(kwargs, 4000),
        )
        print(f"\n  {_MAGENTA}{_DIM}* Thinking...{_RESET}", end="", flush=True)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        _log.info(
            "LLM_START run_id=%s serialized=%s\nprompts=%s\nkwargs=%s",
            run_id,
            _safe_json(serialized, 8000),
            _safe_json(prompts, 16000),
            _safe_json(kwargs, 4000),
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        _log.error(
            "LLM_ERROR run_id=%s error=%s kwargs=%s",
            run_id,
            error,
            _safe_json(kwargs, 4000),
        )
        print(f"\r  {_RED}[X] LLM error:{_RESET} {error!s}", flush=True, file=sys.stderr)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            gens = getattr(response, "generations", None)
            flat = []
            if gens:
                for gen_list in gens:
                    for g in gen_list:
                        t = getattr(g, "text", None)
                        if t:
                            flat.append(t)
                        elif getattr(g, "message", None) is not None:
                            flat.append(str(g.message))
            payload = {"generations_text": flat, "llm_output": getattr(response, "llm_output", None)}
        except Exception as e:
            payload = {"error_serializing": str(e), "repr": repr(response)}
        _log.info(
            "LLM_END run_id=%s\nresponse=%s\nkwargs=%s",
            run_id,
            _safe_json(payload, 50000),
            _safe_json(kwargs, 4000),
        )
        # Clear thinking indicator
        print(f"\r  {' ' * 30}\r", end="", flush=True)

    # ---- Tool events ----

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        name = (serialized or {}).get("name", "?")
        self._tool_start_times[run_id] = time.time()

        _log.info(
            "TOOL_START run_id=%s name=%s\ninput_str=%s\ninputs=%s\nkwargs=%s",
            run_id,
            name,
            input_str,
            _safe_json(inputs, 20000),
            _safe_json(kwargs, 4000),
        )

        # Parse arguments for display
        try:
            args = json.loads(input_str) if isinstance(input_str, str) else (inputs or {})
        except (json.JSONDecodeError, TypeError):
            args = {"input": input_str}

        # Permission check for unsafe tools
        if not is_safe(name):
            approved = request_approval(name, args)
            if not approved:
                self._denied_runs.add(run_id)
                return

        # Verbose tool output
        args_compact = ", ".join(f"{k}={v!r}" for k, v in args.items())
        if len(args_compact) > 100:
            args_compact = args_compact[:97] + "..."
        print(f"  {_MAGENTA}>> {name}{_RESET} {_DIM}{args_compact}{_RESET}", flush=True)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        elapsed = time.time() - self._tool_start_times.pop(run_id, time.time())
        out_str = str(output)
        if len(out_str) > 50000:
            out_str = out_str[:50000] + "\n... [truncated]"

        _log.info(
            "TOOL_END run_id=%s elapsed=%.3fs\noutput=%s\nkwargs=%s",
            run_id,
            elapsed,
            out_str,
            _safe_json(kwargs, 4000),
        )

        if run_id in self._denied_runs:
            self._denied_runs.discard(run_id)
            print(f"  {_YELLOW}-- Skipped (denied by user){_RESET}", flush=True)
            return

        # Show brief result
        preview = out_str[:80] + ("..." if len(out_str) > 80 else "")
        print(f"  {_GREEN}[ok]{_RESET} {_DIM}({elapsed:.0f}ms){_RESET} {_DIM}{preview}{_RESET}", flush=True)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        elapsed = time.time() - self._tool_start_times.pop(run_id, time.time())
        _log.exception(
            "TOOL_ERROR run_id=%s error=%s kwargs=%s",
            run_id,
            error,
            _safe_json(kwargs, 4000),
        )
        print(
            f"  {_RED}[X] Error ({elapsed:.0f}ms):{_RESET} {error!s}",
            flush=True,
            file=sys.stderr,
        )

    # ---- Chain events (file-log only) ----

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        _log.debug(
            "CHAIN_START run_id=%s name=%s inputs=%s",
            run_id,
            (serialized or {}).get("name", (serialized or {}).get("id", "?")),
            _safe_json(inputs, 20000),
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        _log.debug(
            "CHAIN_END run_id=%s outputs=%s",
            run_id,
            _safe_json(outputs, 20000),
        )
