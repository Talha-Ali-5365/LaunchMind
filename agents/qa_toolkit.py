"""GitHub PR inline comment tool for the QA agent."""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from services.github_service import GitHubService


class QAToolkit:
    """Inline review comments on a single PR file path."""

    def __init__(
        self,
        gh: GitHubService,
        pull_number: int,
        head_sha: str,
        path: str = "index.html",
    ) -> None:
        self._gh = gh
        self._pull_number = pull_number
        self._head_sha = head_sha
        self._path = path

    def add_pr_inline_comment(self, line: int, body: str) -> str:
        """Add one inline review comment on the HTML file in the PR.

        Args:
            line: 1-based line number in the file at ``head_sha``.
            body: Comment body (markdown).

        Returns:
            Short confirmation string.
        """
        line_no = max(1, int(line))
        self._gh.create_pull_comment(
            self._pull_number,
            body=body.strip(),
            commit_id=self._head_sha,
            path=self._path,
            line=line_no,
        )
        return f"comment_posted_line_{line_no}"


def build_qa_structured_tools(toolkit: QAToolkit) -> list[StructuredTool]:
    """Build LangChain tools from a ``QAToolkit`` instance.

    Args:
        toolkit: Toolkit with GitHub client and PR coordinates.

    Returns:
        Structured tools for the QA deep agent.
    """
    return [
        StructuredTool.from_function(
            func=toolkit.add_pr_inline_comment,
            name="add_pr_inline_comment",
            description="Add a single inline review comment on index.html in the PR.",
        ),
    ]
