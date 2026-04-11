"""Product Deep Agent — structured product spec."""

from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent

from agents.deep_invoke import ainvoke_deep_agent
from core.settings import Settings
from prompts.product import PRODUCT_SYSTEM, PRODUCT_USER_TEMPLATE
from models.agent_outputs import ProductSpecOut
from services.llm import build_chat_model
from utils.structured_parse import parse_structured_llm_json


def build_product_agent(settings: Settings) -> Any:
    """Build the Product deep agent (spec JSON only, no tools).

    Args:
        settings: Application settings.

    Returns:
        Deep Agent runnable.
    """
    model = build_chat_model(settings, agent="product")
    return create_deep_agent(model=model, system_prompt=PRODUCT_SYSTEM, tools=[])


async def product_run(
    agent: Any,
    idea: str,
    task_payload: dict[str, Any],
) -> dict[str, Any]:
    """Produce a validated product specification dict.

    Args:
        agent: Product deep agent instance.
        idea: Startup idea string.
        task_payload: CEO task payload (idea, focus, optional revision feedback).

    Returns:
        Product spec as dict (PRD-shaped).
    """
    prompt = PRODUCT_USER_TEMPLATE.format(
        idea=idea,
        task_json=json.dumps(task_payload, indent=2),
    )
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, ProductSpecOut)
