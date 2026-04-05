"""
Interactive model selector for DesktopLM startup.

Queries Ollama for locally available models, presents a numbered menu,
and lets the user pick or switch to a cloud provider.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def _query_ollama_models() -> list[dict[str, Any]]:
    """Return a list of locally available Ollama models via the Python client."""
    try:
        import ollama
        response = ollama.list()
        models_raw = response.get("models", [])
        if not models_raw:
            # Newer ollama client returns response as an object with .models
            models_raw = getattr(response, "models", [])
        out = []
        for m in models_raw:
            name = m.get("name", "") or getattr(m, "name", "")
            size = m.get("size", 0) or getattr(m, "size", 0)
            out.append({"name": name, "size_bytes": size})
        return out
    except Exception:
        return []


def _format_size(b: int) -> str:
    if b <= 0:
        return "?"
    gb = b / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.1f} GB"
    return f"{b / (1024 ** 2):.0f} MB"


SUGGESTED_MODELS = [
    "qwen2.5:7b",
    "qwen2.5:3b",
    "llama3.2:3b",
    "mistral:7b",
    "phi3:mini",
    "gemma2:2b",
]


def select_model_interactive() -> dict[str, str]:
    """Interactive model selection.  Returns dict with keys: mode, provider, model, api_key (if cloud).

    Loops until a valid selection is made.
    """
    while True:
        print()
        print("+=========================================+")
        print("|     DesktopLM  Model Selection          |")
        print("+=========================================+")
        print()

        # Discover local models
        local_models = _query_ollama_models()

        if local_models:
            print("  Local models (Ollama):")
            for i, m in enumerate(local_models, 1):
                size = _format_size(m["size_bytes"])
                print(f"    {i}. {m['name']:<30s} ({size})")
        else:
            print("  [!] No local Ollama models found.")
            print("      Pull one with:  ollama pull qwen2.5:7b")
            print()
            print("  Suggested models to pull:")
            for s in SUGGESTED_MODELS:
                print(f"      - {s}")

        print()
        cloud_start = len(local_models) + 1
        print(f"  Cloud providers:")
        print(f"    {cloud_start}. Google Gemini  (needs GOOGLE_API_KEY)")
        print(f"    {cloud_start + 1}. OpenAI        (needs OPENAI_API_KEY)")
        print()

        choice_str = input(f"  Select [1-{cloud_start + 1}]: ").strip()
        if not choice_str:
            continue

        try:
            choice = int(choice_str)
        except ValueError:
            # Maybe they typed a model name directly
            if ":" in choice_str or choice_str in [m["name"] for m in local_models]:
                return {"mode": "local", "provider": "ollama", "model": choice_str}
            print(f"  [X] Invalid choice: {choice_str!r}")
            continue

        # Local model
        if 1 <= choice <= len(local_models):
            model_name = local_models[choice - 1]["name"]
            # Validate the model actually loads
            print(f"\n  Testing {model_name}...", end=" ", flush=True)
            try:
                import ollama
                # Quick ping -- just make sure the model responds
                ollama.chat(model=model_name, messages=[{"role": "user", "content": "hi"}])
                print("OK")
                return {"mode": "local", "provider": "ollama", "model": model_name}
            except Exception as e:
                print(f"FAILED: {e}")
                print("  Please choose another model.\n")
                continue

        # Cloud: Gemini
        if choice == cloud_start:
            api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if not api_key:
                api_key = input("  Enter GOOGLE_API_KEY: ").strip()
            if not api_key:
                print("  [X] No API key provided.")
                continue
            model = input("  Gemini model [gemini-2.0-flash]: ").strip() or "gemini-2.0-flash"
            return {"mode": "cloud", "provider": "gemini", "model": model, "api_key": api_key}

        # Cloud: OpenAI
        if choice == cloud_start + 1:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                api_key = input("  Enter OPENAI_API_KEY: ").strip()
            if not api_key:
                print("  [X] No API key provided.")
                continue
            model = input("  OpenAI model [gpt-4o-mini]: ").strip() or "gpt-4o-mini"
            return {"mode": "cloud", "provider": "openai", "model": model, "api_key": api_key}

        print(f"  [X] Invalid choice: {choice}")
