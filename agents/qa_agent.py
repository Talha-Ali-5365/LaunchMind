"""QA Deep Agent — PR inline comments + verdict JSON."""

from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent

from agents.deep_invoke import ainvoke_deep_agent
from agents.qa_toolkit import QAToolkit, build_qa_structured_tools
from core.settings import Settings
from prompts.qa import QA_SYSTEM, QA_USER_TEMPLATE
from models.agent_outputs import QAReportOut
from services.github_service import GitHubService
from services.llm import build_chat_model
from utils.structured_parse import parse_structured_llm_json


def build_qa_agent(
    settings: Settings,
    gh: GitHubService,
    pull_number: int,
    head_sha: str,
) -> Any:
    """Build QA deep agent with inline PR comment tool.

    Args:
        settings: Application settings.
        gh: GitHub API client.
        pull_number: Pull request number.
        head_sha: Head commit SHA for review comments.

    Returns:
        Deep Agent runnable with QA tools.
    """
    model = build_chat_model(settings, agent="qa")
    toolkit = QAToolkit(gh, pull_number, head_sha)
    tools = build_qa_structured_tools(toolkit)
    return create_deep_agent(model=model, system_prompt=QA_SYSTEM, tools=tools)


async def qa_run(
    agent: Any,
    *,
    spec: dict[str, Any],
    marketing: dict[str, Any],
    pr_url: str,
    html_content: str,
) -> dict[str, Any]:
    """Run QA review: tools (inline comments) + structured verdict JSON.

    Args:
        agent: QA deep agent instance.
        spec: Product specification dict.
        marketing: Marketing output dict.
        pr_url: Pull request URL (context for the model).
        html_content: Landing page HTML to assess.

    Returns:
        QA verdict dict.
    """
    prompt = QA_USER_TEMPLATE.format(
        spec_json=json.dumps(spec, indent=2),
        marketing_json=json.dumps(marketing, indent=2),
        pr_url=pr_url,
        html_content=html_content[:20000],
    )
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, QAReportOut)
