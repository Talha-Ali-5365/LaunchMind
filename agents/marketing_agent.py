"""Marketing Deep Agent — Resend email + Slack Block Kit."""

from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent

from agents.deep_invoke import ainvoke_deep_agent
from agents.marketing_toolkit import MarketingToolkit, build_marketing_structured_tools
from core.settings import Settings
from prompts.marketing import MARKETING_SYSTEM, MARKETING_USER_TEMPLATE
from models.agent_outputs import MarketingCopyOut
from services.llm import build_chat_model
from utils.structured_parse import parse_structured_llm_json


def build_marketing_agent(settings: Settings, pr_url: str) -> Any:
    """Build Marketing deep agent; ``pr_url`` must come from the CEO handoff.

    Args:
        settings: Application settings.
        pr_url: GitHub PR URL injected into Slack tool (not read from Engineer bus).

    Returns:
        Deep Agent runnable with email + Slack tools.
    """
    model = build_chat_model(settings)
    toolkit = MarketingToolkit(settings, pr_url)
    tools = build_marketing_structured_tools(toolkit)
    return create_deep_agent(model=model, system_prompt=MARKETING_SYSTEM, tools=tools)


async def marketing_run(
    agent: Any,
    spec: dict[str, Any],
    pr_url: str,
) -> dict[str, Any]:
    """Generate copy, send email, post Slack; return structured marketing JSON.

    Args:
        agent: Marketing deep agent instance.
        spec: Product specification dict.
        pr_url: Same PR URL as used to construct the agent (CEO-sourced).

    Returns:
        Marketing copy fields as dict.
    """
    prompt = MARKETING_USER_TEMPLATE.format(
        spec_json=json.dumps(spec, indent=2),
        pr_url=pr_url,
    )
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, MarketingCopyOut)
