"""GitHub tool implementations for the Engineer agent (class-based, no nested defs)."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

from langchain_core.tools import StructuredTool

from agents.engineer_context import EngineerContext
from core.settings import Settings
from services.github_service import GitHubService
from services.unsplash_service import search_photos

logger = logging.getLogger(__name__)


class EngineerToolkit:
    """Mutable GitHub operations bound to one engineer run context."""

    def __init__(
        self,
        gh: GitHubService,
        ctx: EngineerContext,
        settings: Settings,
    ) -> None:
        self._gh = gh
        self._ctx = ctx
        self._settings = settings

    def create_github_issue(self, title: str, body: str) -> str:
        """Create the GitHub issue for the landing page work.

        Args:
            title: Issue title.
            body: Issue body (markdown).

        Returns:
            Issue URL or a short status string if already created.
        """
        if self._ctx.issue_url:
            return f"issue_already_created: {self._ctx.issue_url}"
        data = self._gh.create_issue(title.strip(), body.strip())
        self._ctx.issue_url = str(data.get("html_url", ""))
        return self._ctx.issue_url

    def create_engineer_branch(self) -> str:
        """Create a new branch from the repository default branch.

        Returns:
            Branch name or existing branch marker string.
        """
        if self._ctx.branch_name:
            return f"branch_already_created: {self._ctx.branch_name}"
        base_branch = self._gh.get_default_branch()
        base_sha = self._gh.get_branch_sha(base_branch)
        suffix = uuid4().hex[:8]
        name = f"{self._settings.engineer_branch_prefix}-{suffix}"
        try:
            self._gh.create_branch(name, base_sha)
        except Exception:
            name = f"{self._settings.engineer_branch_prefix}-{suffix}-b"
            self._gh.create_branch(name, base_sha)
        self._ctx.branch_name = name
        return self._ctx.branch_name

    def upload_landing_html(self, full_html: str) -> str:
        """Upload or update ``index.html`` on the engineer branch.

        Args:
            full_html: Complete HTML document string.

        Returns:
            Short status message for the agent.
        """
        if not self._ctx.branch_name:
            return "error: create_engineer_branch first"
        self._gh.put_file(
            "index.html",
            full_html,
            "feat: add LaunchMind landing page",
            self._ctx.branch_name,
        )
        self._ctx.last_html = full_html
        return "uploaded index.html"

    def search_unsplash_photos(self, query: str, count: int = 4) -> str:
        """Search Unsplash for photos matching a theme; returns JSON with URLs and attribution.

        Requires ``UNSPLASH_ACCESS_KEY`` in settings. Use 1–2 searches derived from the
        product spec (e.g. industry + audience) before building HTML, then embed ``url``
        values in ``<img src=...>`` and credit photographers in the footer.

        Args:
            query: Search string (e.g. ``modern restaurant interior``, ``laptop workspace``).
            count: Number of images to return (1–10).

        Returns:
            JSON string: ``images`` list with ``url``, ``alt_suggestion``, ``photographer``,
            ``photographer_url``, ``photo_page``; or an ``error`` / ``hint`` if misconfigured.
        """
        key = (self._settings.unsplash_access_key or "").strip()
        if not key:
            return json.dumps(
                {
                    "error": "missing_unsplash_access_key",
                    "hint": "Set UNSPLASH_ACCESS_KEY in .env, or use static Unsplash URLs from your instructions.",
                },
            )
        try:
            n = max(1, min(int(count), 10))
        except (TypeError, ValueError):
            n = 4
        try:
            rows = search_photos(self._settings, query=query.strip(), per_page=n)
        except Exception as e:
            logger.warning("Unsplash search failed: %s", e)
            return json.dumps({"error": str(e), "query": query.strip()})
        if not rows:
            return json.dumps(
                {"query": query.strip(), "images": [], "note": "no_results"},
            )
        return json.dumps({"query": query.strip(), "images": rows}, indent=2)

    def open_pull_request(self, title: str, body: str) -> str:
        """Open a pull request from the engineer branch to the default branch.

        Args:
            title: PR title.
            body: PR description.

        Returns:
            PR URL or a short status if already open.
        """
        if not self._ctx.branch_name:
            return "error: branch missing"
        if self._ctx.pr_url:
            return f"pr_already_open: {self._ctx.pr_url}"
        base_branch = self._gh.get_default_branch()
        data = self._gh.create_pull_request(
            title=title.strip(),
            body=body.strip(),
            head=self._ctx.branch_name,
            base=base_branch,
        )
        self._ctx.pr_url = str(data.get("html_url", ""))
        num = data.get("number")
        self._ctx.pr_number = int(num) if num is not None else None
        return self._ctx.pr_url


def build_engineer_structured_tools(toolkit: EngineerToolkit) -> list[StructuredTool]:
    """Build LangChain tools from an ``EngineerToolkit`` instance.

    Args:
        toolkit: Configured toolkit (GitHub + context + settings).

    Returns:
        List of structured tools passed to ``create_deep_agent``.
    """
    return [
        StructuredTool.from_function(
            func=toolkit.create_github_issue,
            name="create_github_issue",
            description="Create the GitHub issue for the landing page work.",
        ),
        StructuredTool.from_function(
            func=toolkit.create_engineer_branch,
            name="create_engineer_branch",
            description="Create a new branch from the repo default branch for agent work.",
        ),
        StructuredTool.from_function(
            func=toolkit.search_unsplash_photos,
            name="search_unsplash_photos",
            description=(
                "Search Unsplash for photo URLs and attribution (needs UNSPLASH_ACCESS_KEY). "
                "Call with keywords from the product spec before upload_landing_html; embed "
                "returned url values in img tags and credit photographers in the footer."
            ),
        ),
        StructuredTool.from_function(
            func=toolkit.upload_landing_html,
            name="upload_landing_html",
            description="Upload or update index.html on the engineer branch.",
        ),
        StructuredTool.from_function(
            func=toolkit.open_pull_request,
            name="open_pull_request",
            description="Open a pull request from the engineer branch to the default branch.",
        ),
    ]
