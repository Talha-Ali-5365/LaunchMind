"""PRD §4.1 structured agent messages (Pydantic)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

MessageType = Literal["task", "result", "revision_request", "confirmation"]
AgentName = Literal["ceo", "product", "engineer", "marketing", "qa"]


def iso_now() -> str:
    """UTC timestamp in ISO-8601 form used for ``AgentMessage.timestamp``."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AgentMessage(BaseModel):
    """Single message on the bus (PRD schema)."""

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    from_agent: str
    to_agent: str
    message_type: MessageType
    payload: dict[str, Any]
    timestamp: str = Field(default_factory=iso_now)
    parent_message_id: str | None = None

    def model_dump_jsonable(self) -> dict[str, Any]:
        """Serialize to JSON-compatible primitives (for logging or APIs)."""
        return self.model_dump(mode="json")


def new_message(
    *,
    from_agent: str,
    to_agent: str,
    message_type: MessageType,
    payload: dict[str, Any],
    parent_message_id: str | None = None,
) -> AgentMessage:
    """Factory for a valid ``AgentMessage`` with fresh id and timestamp.

    Args:
        from_agent: Sender role name.
        to_agent: Recipient role name.
        message_type: PRD message kind.
        payload: Arbitrary JSON object body.
        parent_message_id: Optional id for threading.

    Returns:
        Constructed ``AgentMessage`` instance.
    """
    return AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        payload=payload,
        parent_message_id=parent_message_id,
    )
