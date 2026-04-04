"""Mutable state shared across Marketing tool invocations in one pipeline run."""

from dataclasses import dataclass, field


@dataclass
class MarketingContext:
    """Ensures at most one launch announcement per run (Slack Block Kit)."""

    slack_launch_posted: bool = field(default=False)
