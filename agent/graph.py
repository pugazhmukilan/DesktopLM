"""LangGraph ReAct agent wired to the unified LLM provider and the tool registry."""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from LLMS.provider import LLMProvider
from agent.system_prompt import AGENT_SYSTEM_PROMPT
from MemoryManager.Orchesterator import MemoryOrchestrator
from tools.registry import build_tools


def build_agent_graph(
    orchestrator: MemoryOrchestrator | None = None,
    provider: LLMProvider | None = None,
):
    """
    Compiled LangGraph agent: model (from provider) + tools + system prompt.
    Accepts an optional provider so the pipeline can rebuild the graph on hot-swap.
    """
    prov = provider or LLMProvider()
    model = prov.get_chat_model()
    tools = build_tools(orchestrator)
    from datetime import datetime
    from pathlib import Path
    from MemoryManager.settings import agent_workspace_path
    
    current_time_str = datetime.now().strftime("%A, %B %d, %Y %H:%M:%S")
    
    # Auto-scan skills directory (portable — works on any machine)
    skills_dir = agent_workspace_path() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    available_skills = "None"
    if skills_dir.exists():
        skills_files = [f.name for f in skills_dir.glob("*.md")]
        if skills_files:
            available_skills = ", ".join(skills_files)

    dynamic_prompt = f"{AGENT_SYSTEM_PROMPT}\n\nAvailable Live Skills (use `read_workspace_file('skills/filename.md')` to read): {available_skills}\n\nThe current date and time is: {current_time_str}"

    return create_react_agent(
        model,
        tools,
        prompt=SystemMessage(content=dynamic_prompt),
    )
