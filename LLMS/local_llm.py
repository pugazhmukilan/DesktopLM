"""
Single local Ollama model for all LLM work. Memory extraction and agent chat
run sequentially (two calls) on the same weights; behavior differs by prompt/options.

Memory extraction uses the system prompt in LLMS/sys_prompt_slm.py (SYSTEM_PROMPT).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import dotenv
import ollama

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

dotenv.load_dotenv()

from LLMS.sys_prompt_slm import SYSTEM_PROMPT as MEMORY_SYSTEM_PROMPT

DEFAULT_MODEL = os.getenv("DESKTOPLM_MODEL", "qwen2.5:7b")

_llm_log = logging.getLogger("desktoplm.llm")

_DEFAULT_AGENT_SYSTEM = (
    "You are a helpful assistant. Use tools when they clearly help answer the user."
)


class LocalLLM:
    def __init__(self, model_name: str | None = None):
        self.model = model_name or DEFAULT_MODEL

    def memory_extract(self, user_input: str) -> dict[str, Any]:
        """Structured memory JSON for routing into stores."""
        from datetime import datetime
        current_time_str = datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
        dynamic_system = f"{MEMORY_SYSTEM_PROMPT}\n\n[IMPORTANT ENFORCEMENT]: The current date and time right now is {current_time_str}. You MUST use this exact time as your baseline for calculating `source_datetime` and relative `interpreted_datetime` values."
        
        messages = [
            {"role": "system", "content": dynamic_system},
            {"role": "user", "content": user_input},
        ]
        _llm_log.info(
            "memory_extract Ollama request model=%s format=json tools=1 messages_chars=%s",
            self.model,
            sum(len(str(m.get("content", ""))) for m in messages),
        )
        _llm_log.debug(
            "memory_extract request messages=\n%s",
            json.dumps(messages, ensure_ascii=False, default=str, indent=2)[:80000],
        )
        response = ollama.chat(
            model=self.model,
            messages=messages,
            format="json",
        )
        _llm_log.info("memory_extract Ollama response received")
        _llm_log.debug(
            "memory_extract Ollama response (full)=\n%s",
            json.dumps(response, ensure_ascii=False, default=str, indent=2)[:80000],
        )
        msg = response.message if hasattr(response, "message") else response.get("message", {})
        content = msg.content if hasattr(msg, "content") else msg.get("content", "")
        if not content:
            return {}
        return json.loads(content)

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[Any] | None = None,
        format: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Raw Ollama chat response (message may include content and tool_calls)."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if format is not None:
            kwargs["format"] = format
        if options:
            kwargs["options"] = options
        preview = {k: v for k, v in kwargs.items() if k != "tools"}
        preview["tools"] = f"<{len(kwargs.get('tools') or [])} tool(s)>" if kwargs.get("tools") is not None else None
        _llm_log.info("chat Ollama request model=%s fields=%s", self.model, list(kwargs.keys()))
        _llm_log.debug("chat Ollama request (serializable preview)=\n%s", json.dumps(preview, default=str, indent=2)[:80000])
        resp = ollama.chat(**kwargs)
        _llm_log.debug(
            "chat Ollama response (full)=\n%s",
            json.dumps(resp, default=str, indent=2)[:80000],
        )
        # Convert ChatResponse to dict for downstream compatibility
        if hasattr(resp, "model_dump"):
            return resp.model_dump()
        if hasattr(resp, "__dict__") and not isinstance(resp, dict):
            return dict(resp)
        return resp

    def agent_chat(
        self,
        user_prompt: str,
        *,
        system_prompt: str | None = None,
        tools: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Single-turn agent call with optional tools (sequential pipeline step 2)."""
        sys_content = system_prompt or _DEFAULT_AGENT_SYSTEM
        messages = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_prompt},
        ]
        return self.chat(messages, tools=tools or [])

    def sequential_memory_then_agent(
        self,
        user_input: str,
        *,
        agent_system_prompt: str | None = None,
        tools: list[Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Run memory extraction then agent chat on the same model, in order.
        Does not persist memory; caller handles storage after step 1.
        """
        memory = self.memory_extract(user_input)
        agent_response = self.agent_chat(
            user_input,
            system_prompt=agent_system_prompt,
            tools=tools,
        )
        return memory, agent_response


def _print_json(label: str, data: Any) -> None:
    print(f"\n--- {label} ---")
    try:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except (TypeError, ValueError):
        print(repr(data))


if __name__ == "__main__":
    # Memory extraction, sequential flow, and agent chat — runs only when executing this file.
    prompts: list[tuple[str, str]] = [
        (
            "reminder_todo",
            "I must submit the report by Friday 5pm and call my dentist tomorrow at 2 PM.",
        ),
        (
            "preference",
            "I focus better with classical music and I prefer short, clear explanations.",
        ),
        (
            "episodic",
            "Last summer I spent a week hiking in the Alps; it was exhausting but amazing.",
        ),
        (
            "external_mode",
            "Here is an article pasted for analysis only: The stock market rose 2% today on tech earnings. "
            "Summarize it for me.",
        ),
        (
            "minimal",
            "Hi.",
        ),
    ]

    llm = LocalLLM()
    print(f"Model: {llm.model}")
    print("=" * 60)

    for name, text in prompts:
        print(f"\n{'#' * 60}\nPrompt [{name}]: {text[:120]}{'…' if len(text) > 120 else ''}\n{'#' * 60}")
        try:
            mem = llm.memory_extract(text)
            _print_json("memory_extract (JSON)", mem)
        except Exception as e:
            print(f"memory_extract failed: {e!r}")

    seq_user = (
        "Remember I have a team sync every Monday at 9am. "
        "Also, what is a good one-line summary of that commitment?"
    )
    print(f"\n{'=' * 60}\nsequential_memory_then_agent\n{'=' * 60}")
    try:
        memory, agent_raw = llm.sequential_memory_then_agent(seq_user)
        _print_json("step 1 memory", memory)
        msg = agent_raw.get("message", {})
        _print_json("step 2 agent message", {"role": msg.get("role"), "content": msg.get("content")})
        if msg.get("tool_calls"):
            _print_json("step 2 tool_calls", msg.get("tool_calls"))
    except Exception as e:
        print(f"sequential_memory_then_agent failed: {e!r}")

    print(f"\n{'=' * 60}\nagent_chat (single turn)\n{'=' * 60}")
    try:
        r = llm.agent_chat("Reply in one sentence: what is 19 + 23?")
        m = r.get("message", {})
        print(m.get("content", "").strip() or repr(m))
    except Exception as e:
        print(f"agent_chat failed: {e!r}")
