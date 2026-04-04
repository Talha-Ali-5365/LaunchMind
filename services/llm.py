"""Shared ChatOpenAI factory for Deep Agents."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from core.settings import Settings


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """Construct a ``ChatOpenAI`` client from settings (OpenAI-compatible endpoint).

    Args:
        settings: Loaded env (model name, API key, base URL).

    Returns:
        Configured chat model for Deep Agents.
    """
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or None,
        base_url=settings.openai_base_url or None,
        temperature=0.2,
    )
