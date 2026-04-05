"""Bundled demos callable from `desktoplm demo-memory`."""

from __future__ import annotations

from MemoryManager.Orchesterator import MemoryOrchestrator


def _ensure_log():
    try:
        from agent.run_logging import configure_logging

        configure_logging()
    except ImportError:
        pass

MEMORY_WRITE_DEMO_PROMPT = """
Hey, dumping a bunch of context in one go so you know how I'm wired.

Work: our Q2 roadmap review is scheduled for next Tuesday at 2 PM in the main conference room.
I promised my manager I'd send the draft architecture doc the evening before, so that's a hard commitment for me.

Personal health: I have a dentist cleaning next Wednesday at 10:30 AM — I tend to cancel these if I don't put them in writing, so I need that locked in.

Family: I told my sister I'd call her this Sunday afternoon to catch up; I don't want to flake again.

How I like to work: I focus best with lo-fi or instrumental music, not lyrics. Long walls of text make me tune out — short bullet answers help.

Something that happened: last month I spoke at a small local meetup about side projects; I was nervous but it went fine and people asked good questions.

Constraints: I'm trying not to take meetings after 6 PM on weekdays so I can cook dinner.

Random vent: this week has been a lot of context switching and I'm tired — not asking you to fix it, just saying.

Also here's a pasted blurb from a newsletter (not about me): "Global chip demand rose 4% quarter over quarter." I'm only sharing it because it was in my inbox — you don't need to treat that as a fact about my life.

Thanks — that's everything for now.
""".strip()


def run_memory_write_demo() -> int:
    """One large message: memory_extract + route to stores only (no LangGraph)."""
    _ensure_log()
    orchestrator = MemoryOrchestrator()
    print("=" * 72)
    print("Memory write demo (extract + route to stores)")
    print("=" * 72)
    print(f"Message length: {len(MEMORY_WRITE_DEMO_PROMPT)} chars\n")
    orchestrator.store_memory_from_prompt(MEMORY_WRITE_DEMO_PROMPT)
    print("Done.")
    return 0
