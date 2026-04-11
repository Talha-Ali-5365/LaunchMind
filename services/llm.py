"""Shared ChatOpenAI factory for Deep Agents."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from core.settings import AgentLLMRole, Settings


def build_chat_model(settings: Settings, *, agent: AgentLLMRole) -> ChatOpenAI:
    """Construct a ``ChatOpenAI`` client from settings (OpenAI-compatible endpoint).

    Args:
        settings: Loaded env (API key, base URL, and per-agent or default model name).
        agent: Which pipeline agent this client is for (selects ``OPENAI_MODEL_*``).

    Returns:
        Configured chat model for Deep Agents.
    """
    return ChatOpenAI(
        model=settings.openai_model_for_agent(agent),
        api_key=settings.openai_api_key or None,
        base_url=settings.openai_base_url or None,
        temperature=0.2,
    )
