"""Async Deep Agent invocation with retries."""

from __future__ import annotations

from typing import Any

from utils.llm_output import last_message_text
from utils.retry import with_retry_async


class _DeepAgentAinvoke:
    """Callable holder for a single agent.ainvoke (avoids nested functions)."""

    def __init__(self, agent: Any, user_content: str) -> None:
        self._agent = agent
        self._user_content = user_content

    async def run(self) -> dict[str, Any]:
        """Execute one ainvoke with the configured user message."""
        return await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": self._user_content}]}
        )


async def ainvoke_deep_agent(agent: Any, user_content: str) -> str:
    """Run a deep agent asynchronously and return the last assistant text.

    Args:
        agent: Compiled LangGraph / Deep Agent runnable supporting ``ainvoke``.
        user_content: User message string.

    Returns:
        Normalized plain-text content of the final assistant message.
    """
    runner = _DeepAgentAinvoke(agent, user_content)
    result = await with_retry_async(
        runner.run,
        attempts=3,
        operation="deep_agent.ainvoke",
    )
    return last_message_text(result)
