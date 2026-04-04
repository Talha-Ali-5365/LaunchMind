"""Deterministic phase machine: bus traffic, CEO reviews, QA loop, final Slack."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from agents.ceo_agent import (
    build_ceo_agent,
    ceo_decompose,
    ceo_final_summary_text,
    ceo_review_engineer,
    ceo_review_product,
    ceo_review_qa,
)
from agents.engineer_agent import (
    EngineerContext,
    build_engineer_agent,
    engineer_revision_run,
    engineer_run,
)
from agents.marketing_agent import build_marketing_agent, marketing_run
from agents.product_agent import build_product_agent, product_run
from agents.qa_agent import build_qa_agent, qa_run
from core.message_bus import MessageBus
from core.settings import Settings, get_settings
from models.messages import AgentMessage, new_message
from services.github_service import GitHubService, parse_pull_number_from_url
from services.run_log import save_run_output
from services.slack_service import post_ceo_team_summary

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    """UTC timestamp with fractional seconds for run log boundaries."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _bus_verbose_on_message(m: AgentMessage) -> None:
    """Print and log one bus message (hook for demos)."""
    msg = (
        f"[bus] from={m.from_agent} to={m.to_agent} type={m.message_type} "
        f"id={m.message_id}"
    )
    logger.info(msg)
    print(msg, flush=True)


def _verbose_log_line(msg: str) -> None:
    """Print and log a pipeline phase line."""
    logger.info(msg)
    print(msg, flush=True)


def make_verbose_bus() -> tuple[MessageBus, Callable[[str], None]]:
    """Create a bus with print hook and return the bus plus a log callable.

    Returns:
        ``(bus, log_fn)`` where ``log_fn`` mirrors phase banners to stdout.
    """
    bus = MessageBus()
    bus.set_print_hook(_bus_verbose_on_message)
    return bus, _verbose_log_line


async def run_pipeline_async(
    idea: str,
    *,
    settings: Settings | None = None,
    verbose: bool = True,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the full LaunchMind pipeline asynchronously.

    Args:
        idea: Startup idea string.
        settings: Optional settings override; defaults to ``get_settings()``.
        verbose: When True, attach bus print hook and stdout phase banners.
        run_id: Optional stable id for the run log file (defaults to a new UUID).

    Returns:
        Artifacts dict including ``message_history``, ``run_id``, ``run_output_dir``,
        ``run_log_path``, and ``landing_page_path`` when the landing HTML was saved.
    """
    settings = settings or get_settings()
    rid = run_id or str(uuid.uuid4())
    started_at = _utc_iso()
    if verbose:
        bus, log = make_verbose_bus()
    else:
        bus = MessageBus()
        log = logger.info

    try:
        result = await _run_pipeline_core(idea, settings, bus, log)
        finished_at = _utc_iso()
        landing_html = result.pop("landing_html", None)
        out_dir = save_run_output(
            settings,
            run_id=rid,
            idea=idea,
            started_at=started_at,
            finished_at=finished_at,
            status="completed",
            error=None,
            artifacts=result,
            html_content=landing_html,
        )
        result["run_id"] = rid
        if out_dir is not None:
            result["run_output_dir"] = str(out_dir)
            result["run_log_path"] = str(out_dir / "run_log.json")
            if landing_html is not None:
                result["landing_page_path"] = str(out_dir / "index.html")
        return result
    except Exception as e:
        finished_at = _utc_iso()
        partial: dict[str, Any] = {
            "idea": idea,
            "message_history": [m.model_dump(mode="json") for m in bus.history()],
            "errors": [str(e)],
        }
        save_run_output(
            settings,
            run_id=rid,
            idea=idea,
            started_at=started_at,
            finished_at=finished_at,
            status="failed",
            error=str(e),
            artifacts=partial,
            html_content=None,
        )
        raise


def run_pipeline_sync(
    idea: str,
    *,
    settings: Settings | None = None,
    verbose: bool = True,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper for CLI and blocking callers.

    Args:
        idea: Startup idea string.
        settings: Optional settings override.
        verbose: Forwarded to ``run_pipeline_async``.
        run_id: Optional run id for JSON log filename.

    Returns:
        Same as ``run_pipeline_async``.
    """
    return asyncio.run(
        run_pipeline_async(idea, settings=settings, verbose=verbose, run_id=run_id),
    )


async def _run_pipeline_core(
    idea: str,
    settings: Settings,
    bus: MessageBus,
    log: Callable[..., None],
) -> dict[str, Any]:
    """Internal async pipeline implementation."""
    artifacts: dict[str, Any] = {"idea": idea}
    errors: list[str] = []

    ceo_agent = build_ceo_agent(settings)
    product_agent = build_product_agent(settings)

    log("--- CEO: decompose idea ---")
    decompose = await ceo_decompose(ceo_agent, idea)
    artifacts["decompose"] = decompose
    bus.send(
        new_message(
            from_agent="ceo",
            to_agent="ceo",
            message_type="confirmation",
            payload={"phase": "decompose", "detail": decompose},
        )
    )

    pt = decompose.get("product_task")
    if isinstance(pt, dict):
        focus = pt.get("focus") or "Define personas, top 5 features, and user stories."
    else:
        focus = getattr(pt, "focus", None) or "Define personas, top 5 features, and user stories."

    product_task: dict[str, Any] = {"idea": idea, "focus": focus}
    spec: dict[str, Any] | None = None

    log("--- Product loop (CEO review) ---")
    for round_idx in range(settings.max_revision_rounds):
        bus.send(
            new_message(
                from_agent="ceo",
                to_agent="product",
                message_type="task",
                payload=product_task,
            )
        )
        spec = await product_run(product_agent, idea, product_task)
        review = await ceo_review_product(ceo_agent, idea, spec)
        bus.send(
            new_message(
                from_agent="ceo",
                to_agent="ceo",
                message_type="confirmation",
                payload={
                    "phase": "review_product",
                    "round": round_idx + 1,
                    "detail": review,
                },
            )
        )
        if review.get("acceptable"):
            break
        bus.send(
            new_message(
                from_agent="ceo",
                to_agent="product",
                message_type="revision_request",
                payload={"feedback": review.get("feedback", "")},
            )
        )
        product_task = {
            "idea": idea,
            "focus": focus,
            "revision_feedback": review.get("feedback", ""),
        }
    else:
        msg = "Product spec not accepted within max_revision_rounds"
        errors.append(msg)
        raise RuntimeError(msg)

    assert spec is not None
    artifacts["product_spec"] = spec

    bus.send(
        new_message(
            from_agent="product",
            to_agent="engineer",
            message_type="result",
            payload={"product_spec": spec},
        )
    )
    bus.send(
        new_message(
            from_agent="product",
            to_agent="marketing",
            message_type="result",
            payload={"product_spec": spec},
        )
    )
    bus.send(
        new_message(
            from_agent="product",
            to_agent="ceo",
            message_type="confirmation",
            payload={"product_ready": True},
        )
    )

    log("--- Engineer: GitHub ---")
    gh = GitHubService(settings)
    ctx = EngineerContext()
    eng_agent = build_engineer_agent(settings, gh, ctx)

    try:
        await engineer_run(eng_agent, spec)
    except Exception as e:
        errors.append(f"engineer: {e}")
        log(f"[error] engineer: {e}")
        bus.send(
            new_message(
                from_agent="ceo",
                to_agent="ceo",
                message_type="result",
                payload={"status": "failed", "phase": "engineer", "error": str(e)},
            )
        )
        raise

    if not ctx.pr_url:
        raise RuntimeError("Engineer did not open a pull request")

    bus.send(
        new_message(
            from_agent="engineer",
            to_agent="ceo",
            message_type="result",
            payload={
                "issue_url": ctx.issue_url,
                "pr_url": ctx.pr_url,
                "branch": ctx.branch_name,
            },
        )
    )
    artifacts["github"] = {
        "issue_url": ctx.issue_url,
        "pr_url": ctx.pr_url,
        "branch": ctx.branch_name,
    }

    log("--- CEO: review engineer output ---")
    eng_rev = await ceo_review_engineer(
        ceo_agent,
        idea,
        str(spec.get("value_proposition", "")),
        json.dumps(artifacts["github"], indent=2),
    )
    bus.send(
        new_message(
            from_agent="ceo",
            to_agent="ceo",
            message_type="confirmation",
            payload={"phase": "review_engineer", "detail": eng_rev},
        )
    )
    if not eng_rev.get("acceptable", True):
        bus.send(
            new_message(
                from_agent="ceo",
                to_agent="engineer",
                message_type="revision_request",
                payload={"feedback": eng_rev.get("feedback", "")},
            )
        )
        await engineer_revision_run(
            eng_agent,
            html_excerpt=ctx.last_html or "",
            feedback=str(eng_rev.get("feedback", "")),
            spec=spec,
        )

    log("--- CEO to marketing: PR URL handoff (before Slack) ---")
    bus.send(
        new_message(
            from_agent="ceo",
            to_agent="marketing",
            message_type="task",
            payload={
                "pr_url": ctx.pr_url,
                "note": "Send cold email and post Block Kit launch to Slack.",
            },
        )
    )
    m_agent = build_marketing_agent(settings, ctx.pr_url)
    marketing_copy = await marketing_run(m_agent, spec, ctx.pr_url)
    artifacts["marketing"] = marketing_copy
    bus.send(
        new_message(
            from_agent="marketing",
            to_agent="ceo",
            message_type="result",
            payload=marketing_copy,
        )
    )

    pr_num = parse_pull_number_from_url(ctx.pr_url)
    if pr_num is None:
        raise RuntimeError("Could not parse pull request number from URL")
    pr_data = gh.get_pull(pr_num)
    head_sha = str(pr_data["head"]["sha"])
    html_content = gh.get_file_content("index.html", head_sha)

    log("--- QA: PR review ---")
    qa_agent = build_qa_agent(settings, gh, pr_num, head_sha)
    qa_report = await qa_run(
        qa_agent,
        spec=spec,
        marketing=marketing_copy,
        pr_url=ctx.pr_url,
        html_content=html_content,
    )
    artifacts["qa"] = qa_report
    bus.send(
        new_message(
            from_agent="qa",
            to_agent="ceo",
            message_type="result",
            payload=qa_report,
        )
    )

    log("--- CEO / QA revision loop ---")
    last_ceo_q_review: dict[str, Any] = {}
    for qa_round in range(settings.max_revision_rounds):
        ceo_q = await ceo_review_qa(ceo_agent, qa_report)
        last_ceo_q_review = ceo_q
        bus.send(
            new_message(
                from_agent="ceo",
                to_agent="ceo",
                message_type="confirmation",
                payload={"phase": "review_qa", "round": qa_round + 1, "detail": ceo_q},
            )
        )
        if qa_report.get("verdict") == "pass" and ceo_q.get("acceptable", True):
            break
        if qa_round >= settings.max_revision_rounds - 1:
            break
        feedback = ceo_q.get("feedback") or "Address QA findings."
        escalate = ceo_q.get("escalate_to", "engineer")
        if escalate == "marketing":
            bus.send(
                new_message(
                    from_agent="ceo",
                    to_agent="marketing",
                    message_type="revision_request",
                    payload={"feedback": feedback},
                )
            )
            m_agent = build_marketing_agent(settings, ctx.pr_url)
            marketing_copy = await marketing_run(m_agent, spec, ctx.pr_url)
            artifacts["marketing"] = marketing_copy
        else:
            bus.send(
                new_message(
                    from_agent="ceo",
                    to_agent="engineer",
                    message_type="revision_request",
                    payload={"feedback": feedback},
                )
            )
            await engineer_revision_run(
                eng_agent,
                html_excerpt=html_content,
                feedback=feedback,
                spec=spec,
            )
        pr_data = gh.get_pull(pr_num)
        head_sha = str(pr_data["head"]["sha"])
        html_content = gh.get_file_content("index.html", head_sha)
        qa_agent = build_qa_agent(settings, gh, pr_num, head_sha)
        qa_report = await qa_run(
            qa_agent,
            spec=spec,
            marketing=marketing_copy,
            pr_url=ctx.pr_url,
            html_content=html_content,
        )
        artifacts["qa"] = qa_report
        bus.send(
            new_message(
                from_agent="qa",
                to_agent="ceo",
                message_type="result",
                payload=qa_report,
            )
        )

    log("--- CEO: final Slack summary ---")
    qa_agent_verdict = qa_report.get("verdict")
    ceo_accepted_qa = bool(last_ceo_q_review.get("acceptable"))
    qa_announced_ok = qa_agent_verdict == "pass" or ceo_accepted_qa
    summary_ctx = {
        "idea": idea,
        "pr_url": ctx.pr_url,
        "issue_url": ctx.issue_url,
        "value_proposition": spec.get("value_proposition"),
        "qa_verdict": qa_agent_verdict,
        "marketing_tagline": marketing_copy.get("tagline"),
        "errors": errors,
        "slack_summary_facts": {
            "email_marketing_phase_completed": True,
            "email_marketing_note": (
                "Marketing finished successfully in this run, including the cold-email tool step; "
                "do not claim the email was skipped unless `errors` below is non-empty with an email-related entry."
            ),
            "qa_agent_verdict": qa_agent_verdict,
            "ceo_accepted_latest_qa_review": ceo_accepted_qa,
            "announce_qa_as_success": qa_announced_ok,
            "qa_summary_line": (
                "QA: passed (agent verdict pass or CEO accepted the latest QA cycle)."
                if qa_announced_ok
                else f"QA: latest agent verdict was {qa_agent_verdict!r}; CEO did not accept—note follow-ups."
            ),
            "email_summary_line": (
                "Email: yes — marketing phase completed (cold email sent via configured provider)."
            ),
        },
    }
    summary_text = await ceo_final_summary_text(ceo_agent, summary_ctx)
    artifacts["ceo_final_summary"] = summary_text
    post_ceo_team_summary(settings, summary_text)

    history_dump = [m.model_dump(mode="json") for m in bus.history()]
    artifacts["message_history"] = history_dump
    artifacts["errors"] = errors
    artifacts["landing_html"] = html_content
    return artifacts


def run_pipeline_for_job(idea: str, job_id: str) -> dict[str, Any]:
    """Run pipeline inside a worker thread (async job API).

    Args:
        idea: Startup idea from ``POST /runs``.
        job_id: Job UUID; used as ``run_id`` for the JSON run log filename.

    Returns:
        Artifacts dict or raises on failure.
    """
    return asyncio.run(
        run_pipeline_async(
            idea,
            settings=get_settings(),
            verbose=False,
            run_id=job_id,
        ),
    )
