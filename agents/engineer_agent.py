"""Engineer Deep Agent — GitHub + landing HTML."""

from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent

from agents.deep_invoke import ainvoke_deep_agent
from agents.engineer_context import EngineerContext
from agents.engineer_toolkit import EngineerToolkit, build_engineer_structured_tools
from core.settings import Settings
from prompts.engineer import ENGINEER_REVISION_TEMPLATE, ENGINEER_SYSTEM, ENGINEER_USER_TEMPLATE
from models.agent_outputs import EngineerResultOut
from services.github_service import GitHubService
from services.llm import build_chat_model
from utils.structured_parse import parse_structured_llm_json


def build_engineer_agent(
    settings: Settings,
    gh: GitHubService,
    ctx: EngineerContext,
) -> Any:
    """Build the Engineer deep agent with GitHub structured tools.

    Args:
        settings: Application settings.
        gh: GitHub API client.
        ctx: Mutable per-run engineer context (URLs, branch, HTML).

    Returns:
        Deep Agent runnable with GitHub tools.
    """
    model = build_chat_model(settings, agent="engineer")
    toolkit = EngineerToolkit(gh, ctx, settings)
    tools = build_engineer_structured_tools(toolkit)
    return create_deep_agent(model=model, system_prompt=ENGINEER_SYSTEM, tools=tools)


async def engineer_run(agent: Any, spec: dict[str, Any]) -> dict[str, Any]:
    """Run one engineer pass: tools + final JSON summary.

    Args:
        agent: Engineer deep agent instance.
        spec: Product specification dict.

    Returns:
        Parsed engineer result dict (URLs, branch, summary).
    """
    prompt = ENGINEER_USER_TEMPLATE.format(spec_json=json.dumps(spec, indent=2))
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, EngineerResultOut)


async def engineer_revision_run(
    agent: Any,
    *,
    html_excerpt: str,
    feedback: str,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Run an engineer revision pass after CEO/QA feedback.

    Args:
        agent: Engineer deep agent instance.
        html_excerpt: Prior HTML (truncated) for context.
        feedback: Revision instructions.
        spec: Product specification dict.

    Returns:
        Parsed engineer result dict.
    """
    prompt = ENGINEER_REVISION_TEMPLATE.format(
        spec_json=json.dumps(spec, indent=2),
        html_excerpt=html_excerpt[:12000],
        feedback=feedback,
    )
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, EngineerResultOut)
