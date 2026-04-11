"""CEO Deep Agent — decomposition, reviews, and final summary."""

from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent

from agents.deep_invoke import ainvoke_deep_agent
from core.settings import Settings
from prompts.ceo import (
    CEO_SYSTEM,
    DECOMPOSE_USER_TEMPLATE,
    FINAL_SUMMARY_TEMPLATE,
    REVIEW_ENGINEER_TEMPLATE,
    REVIEW_PRODUCT_TEMPLATE,
    REVIEW_QA_TEMPLATE,
)
from models.agent_outputs import (
    CEODecomposeOut,
    CEOReviewEngineerOut,
    CEOReviewProductOut,
    CEOReviewQAOut,
)
from services.llm import build_chat_model
from utils.structured_parse import parse_structured_llm_json


def build_ceo_agent(settings: Settings) -> Any:
    """Build a Deep Agent for CEO reasoning (no custom tools).

    Args:
        settings: Loaded application settings (API keys, model name).

    Returns:
        Deep Agent runnable from ``deepagents.create_deep_agent``.
    """
    model = build_chat_model(settings, agent="ceo")
    return create_deep_agent(model=model, system_prompt=CEO_SYSTEM, tools=[])


async def ceo_decompose(agent: Any, idea: str) -> dict[str, Any]:
    """Decompose the startup idea into delegated tasks (structured JSON).

    Args:
        agent: CEO deep agent instance.
        idea: Raw startup idea text.

    Returns:
        Parsed decomposition dict (validated via PydanticOutputParser path).
    """
    text = await ainvoke_deep_agent(agent, DECOMPOSE_USER_TEMPLATE.format(idea=idea))
    return parse_structured_llm_json(text, CEODecomposeOut)


async def ceo_review_product(agent: Any, idea: str, spec: dict[str, Any]) -> dict[str, Any]:
    """LLM-review the product spec for specificity vs the idea.

    Args:
        agent: CEO deep agent instance.
        idea: Original idea text.
        spec: Product specification dict.

    Returns:
        Review verdict and feedback fields as dict.
    """
    prompt = REVIEW_PRODUCT_TEMPLATE.format(
        idea=idea,
        spec_json=json.dumps(spec, indent=2),
    )
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, CEOReviewProductOut)


async def ceo_review_engineer(
    agent: Any,
    idea: str,
    value_prop: str,
    summary: str,
) -> dict[str, Any]:
    """LLM-review high-level engineering output.

    Args:
        agent: CEO deep agent instance.
        idea: Original idea text.
        value_prop: Product value proposition string.
        summary: Engineer summary / metadata text.

    Returns:
        Accept/reject style dict for the pipeline.
    """
    prompt = REVIEW_ENGINEER_TEMPLATE.format(idea=idea, vp=value_prop, summary=summary)
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, CEOReviewEngineerOut)


async def ceo_review_qa(agent: Any, qa_report: dict[str, Any]) -> dict[str, Any]:
    """LLM-review QA structured report and escalation hint.

    Args:
        agent: CEO deep agent instance.
        qa_report: QA verdict payload dict.

    Returns:
        CEO follow-up instructions dict.
    """
    prompt = REVIEW_QA_TEMPLATE.format(qa_json=json.dumps(qa_report, indent=2))
    text = await ainvoke_deep_agent(agent, prompt)
    return parse_structured_llm_json(text, CEOReviewQAOut)


async def ceo_final_summary_text(agent: Any, context: dict[str, Any]) -> str:
    """Generate plain-text Slack body for the final CEO summary.

    Args:
        agent: CEO deep agent instance.
        context: Serializable context for the summary prompt.

    Returns:
        Trimmed assistant text (not JSON).
    """
    prompt = FINAL_SUMMARY_TEMPLATE.format(
        context_json=json.dumps(context, indent=2),
    )
    text = await ainvoke_deep_agent(agent, prompt)
    return text.strip()
