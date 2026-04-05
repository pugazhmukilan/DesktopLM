"""
Unified LLM provider — hot-swappable between Local (Ollama) and Cloud (Gemini / OpenAI).

All providers implement LangChain's BaseChatModel interface, so tools, tool_calls,
and the LangGraph agent work identically regardless of backend.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import dotenv

dotenv.load_dotenv()

logger = logging.getLogger("desktoplm.provider")


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def _build_ollama(model: str, base_url: str | None = None):
    """Create a ChatOllama instance."""
    from langchain_ollama import ChatOllama

    kwargs: dict[str, Any] = {"model": model, "temperature": 0.2}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOllama(**kwargs)


def _build_gemini(model: str, api_key: str):
    """Create a ChatGoogleGenerativeAI instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.2,
        convert_system_message_to_human=True,
    )


def _build_openai(model: str, api_key: str, base_url: str | None = None):
    """Create a ChatOpenAI instance (works with OpenAI, Groq, Together, etc.)."""
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model,
        "api_key": api_key,
        "temperature": 0.2,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


# ---------------------------------------------------------------------------
# LLM Provider (singleton, hot-swappable)
# ---------------------------------------------------------------------------

class LLMProvider:
    """Runtime-swappable LLM provider for DesktopLM.

    Holds the currently active LangChain BaseChatModel and exposes it via
    ``get_chat_model()``.  The agent graph, pipeline, and memory extraction
    all reference the same provider instance.
    """

    _instance: LLMProvider | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._mode: str = "local"           # "local" | "cloud"
        self._provider_name: str = "ollama"  # "ollama" | "gemini" | "openai"
        self._model_name: str = os.getenv("DESKTOPLM_MODEL", "qwen2.5:7b")
        self._chat_model = None
        self._initialized = True

    # ---- public API ----

    def get_chat_model(self):
        """Return the currently active LangChain BaseChatModel."""
        if self._chat_model is None:
            self._build_default()
        return self._chat_model

    def switch_to_local(self, model_name: str) -> dict[str, str]:
        """Switch to a local Ollama model.  Returns info dict."""
        base_url = os.getenv("OLLAMA_HOST") or None
        self._chat_model = _build_ollama(model_name, base_url)
        self._mode = "local"
        self._provider_name = "ollama"
        self._model_name = model_name
        logger.info("Switched to local Ollama model: %s", model_name)
        return self.current_info()

    def switch_to_cloud(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
    ) -> dict[str, str]:
        """Switch to a cloud provider.  Returns info dict."""
        provider = provider.lower().strip()
        if provider == "gemini":
            self._chat_model = _build_gemini(model, api_key)
        elif provider in ("openai", "groq", "together"):
            self._chat_model = _build_openai(model, api_key, base_url)
        else:
            raise ValueError(f"Unknown cloud provider: {provider!r}")
        self._mode = "cloud"
        self._provider_name = provider
        self._model_name = model
        logger.info("Switched to cloud %s model: %s", provider, model)
        return self.current_info()

    def current_info(self) -> dict[str, str]:
        """Return a dict describing the current provider/model."""
        return {
            "mode": self._mode,
            "provider": self._provider_name,
            "model": self._model_name,
        }

    @property
    def model_name(self) -> str:
        return self._model_name

    # ---- internal ----

    def _build_default(self):
        """Build the default model from env vars."""
        mode = os.getenv("DESKTOPLM_LLM_MODE", "local").strip().lower()
        if mode == "cloud":
            provider = os.getenv("DESKTOPLM_CLOUD_PROVIDER", "gemini").strip().lower()
            model = os.getenv("DESKTOPLM_CLOUD_MODEL", "gemini-2.0-flash").strip()
            if provider == "gemini":
                key = os.getenv("GOOGLE_API_KEY", "")
            else:
                key = os.getenv("OPENAI_API_KEY", "")
            if not key:
                logger.warning("Cloud mode but no API key found; falling back to local Ollama")
                self.switch_to_local(self._model_name)
                return
            self.switch_to_cloud(provider, model, key)
        else:
            self.switch_to_local(self._model_name)
