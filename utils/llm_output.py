"""Normalize LangChain / Deep Agents message content to plain text."""

from __future__ import annotations

from typing import Any


def last_message_text(result: dict[str, Any]) -> str:
    """Extract plain text from the last entry in an agent ``invoke``/``ainvoke`` result.

    Args:
        result: Dict containing a ``messages`` list (LangGraph-style).

    Returns:
        Concatenated text content, or empty string if missing.
    """
    messages = result.get("messages") or []
    if not messages:
        return ""
    m = messages[-1]
    content = getattr(m, "content", m)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)
