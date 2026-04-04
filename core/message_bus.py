"""In-process message bus (PRD). Thread-safe with full history for demos."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable

from models.messages import AgentMessage


class MessageBus:
    """Thread-safe inboxes plus append-only history for agent traffic."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inboxes: dict[str, list[AgentMessage]] = defaultdict(list)
        self._history: list[AgentMessage] = []
        self._print_hook: Callable[[AgentMessage], None] | None = None

    def set_print_hook(self, fn: Callable[[AgentMessage], None] | None) -> None:
        """Register a callback invoked after each successful ``send`` (or clear with None)."""
        self._print_hook = fn

    def send(self, message: AgentMessage) -> None:
        """Append ``message`` to the recipient inbox and global history."""
        with self._lock:
            self._inboxes[message.to_agent].append(message)
            self._history.append(message)
            hook = self._print_hook
        if hook is not None:
            hook(message)

    def peek_inbox(self, agent: str) -> list[AgentMessage]:
        """Return a copy of queued messages for ``agent`` without consuming."""
        with self._lock:
            return list(self._inboxes.get(agent, []))

    def drain_inbox(self, agent: str) -> list[AgentMessage]:
        """Pop and return all messages for ``agent``, clearing that inbox."""
        with self._lock:
            inbox = self._inboxes[agent]
            out = inbox[:]
            inbox.clear()
            return out

    def history(self) -> list[AgentMessage]:
        """Return every message ever sent, in order."""
        with self._lock:
            return list(self._history)

    def history_for_agent(self, agent: str) -> list[AgentMessage]:
        """Return messages where ``agent`` is sender or recipient."""
        with self._lock:
            return [
                m
                for m in self._history
                if m.from_agent == agent or m.to_agent == agent
            ]
