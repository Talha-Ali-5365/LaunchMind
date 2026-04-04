"""Lightweight bus + schema tests."""

from core.message_bus import MessageBus
from models.messages import AgentMessage, new_message


class _MessageIdCapture:
    """Collects message ids from a ``MessageBus`` print hook."""

    def __init__(self) -> None:
        self.ids: list[str] = []

    def on_message(self, m: AgentMessage) -> None:
        """Append ``m.message_id`` for assertions."""
        self.ids.append(m.message_id)


def test_bus_history_and_hook() -> None:
    bus = MessageBus()
    cap = _MessageIdCapture()
    bus.set_print_hook(cap.on_message)
    m = new_message(
        from_agent="ceo",
        to_agent="product",
        message_type="task",
        payload={"idea": "x"},
    )
    bus.send(m)
    assert len(bus.history()) == 1
    assert cap.ids == [m.message_id]
    bus.set_print_hook(None)


def test_drain_inbox() -> None:
    bus = MessageBus()
    bus.send(
        new_message(
            from_agent="ceo",
            to_agent="qa",
            message_type="task",
            payload={},
        )
    )
    drained = bus.drain_inbox("qa")
    assert len(drained) == 1
    assert bus.drain_inbox("qa") == []
