"""Mutable state shared by Engineer tools across a run."""

from dataclasses import dataclass


@dataclass
class EngineerContext:
    """URLs and branch name filled incrementally by Engineer tools."""

    branch_name: str | None = None
    issue_url: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    last_html: str | None = None
