"""Resend + Slack tools for the Marketing agent."""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from agents.marketing_context import MarketingContext
from core.settings import Settings
from services.email_service import send_html_email
from services.slack_service import post_launch_blocks


class MarketingToolkit:
    """Outbound email and Slack; ``pr_url`` is fixed for CEO-compliant Slack posts."""

    def __init__(
        self,
        settings: Settings,
        pr_url: str,
        run_ctx: MarketingContext,
    ) -> None:
        self._settings = settings
        self._pr_url = pr_url
        self._run_ctx = run_ctx

    def send_cold_email(self, subject: str, html_body: str) -> str:
        """Send the cold outreach email via Resend.

        Args:
            subject: Email subject line.
            html_body: HTML body content.

        Returns:
            Short status token for the agent transcript.
        """
        send_html_email(
            self._settings,
            subject=subject.strip(),
            html_body=html_body,
        )
        return "email_sent"

    def post_launch_slack(self, tagline: str, description: str) -> str:
        """Post Block Kit launch summary using the CEO-provided PR URL.

        At most **one** launch post per pipeline run (revisions skip a second post).

        Args:
            tagline: Short headline text.
            description: Markdown description for Slack.

        Returns:
            Status token for the agent transcript.
        """
        if self._run_ctx.slack_launch_posted:
            return "slack_launch_skipped_duplicate_run"
        post_launch_blocks(
            self._settings,
            tagline=tagline.strip(),
            description=description.strip(),
            pr_url=self._pr_url,
        )
        self._run_ctx.slack_launch_posted = True
        return "slack_posted"


def build_marketing_structured_tools(toolkit: MarketingToolkit) -> list[StructuredTool]:
    """Build LangChain tools from a ``MarketingToolkit`` instance.

    Args:
        toolkit: Toolkit with settings and bound PR URL.

    Returns:
        Structured tools for the marketing deep agent.
    """
    return [
        StructuredTool.from_function(
            func=toolkit.send_cold_email,
            name="send_cold_email",
            description="Send the cold outreach email via Resend.",
        ),
        StructuredTool.from_function(
            func=toolkit.post_launch_slack,
            name="post_launch_slack",
            description=(
                "Post Block Kit launch summary once per pipeline run. "
                "If the tool returns slack_launch_skipped_duplicate_run, do not call again."
            ),
        ),
    ]
