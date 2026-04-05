"""DesktopLM agent: LangGraph + tools + chat pipeline."""

from __future__ import annotations

__all__ = ["ChatPipeline"]


def __getattr__(name: str):
    if name == "ChatPipeline":
        from agent.pipeline import ChatPipeline

        return ChatPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
