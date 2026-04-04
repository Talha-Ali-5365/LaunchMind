"""Persist each pipeline run under ``output/<run_id>/``: log, PR links, landing HTML."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from core.settings import Settings

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]

# Canonical order and copy for the five LaunchMind agents (PRD roles).
PIPELINE_AGENTS: list[dict[str, str]] = [
    {
        "id": "ceo",
        "title": "CEO",
        "description": (
            "Strategic lead: decomposes the startup idea, reviews product, engineering, "
            "and QA outputs, and posts the final team summary to Slack."
        ),
    },
    {
        "id": "product",
        "title": "Product",
        "description": (
            "Owns the product specification—personas, features, and user stories—"
            "refined with the CEO until accepted."
        ),
    },
    {
        "id": "engineer",
        "title": "Engineer",
        "description": (
            "Builds the landing page on GitHub: issue, branch, commits, and pull request "
            "from the approved spec."
        ),
    },
    {
        "id": "marketing",
        "title": "Marketing",
        "description": (
            "Produces launch messaging: tagline, cold email, and Slack Block Kit, "
            "using the PR URL from the CEO handoff."
        ),
    },
    {
        "id": "qa",
        "title": "QA",
        "description": (
            "Reviews the pull request, HTML, and marketing assets against the product spec "
            "and returns structured findings."
        ),
    },
]

# Artifact keys primarily produced by each agent (for the log “outputs” subsection).
_AGENT_OUTPUT_KEYS: dict[str, tuple[str, ...]] = {
    "ceo": ("decompose", "ceo_final_summary"),
    "product": ("product_spec",),
    "engineer": ("github",),
    "marketing": ("marketing",),
    "qa": ("qa",),
}


def resolve_output_run_dir(settings: Settings, run_id: str) -> Path:
    """Directory for one run: ``<output_dir>/<run_id>/`` (relative paths use repo root)."""
    p = Path(settings.output_dir)
    base = p if p.is_absolute() else REPO_ROOT / p
    return base / run_id


def expected_run_output_dir(settings: Settings, run_id: str) -> Path | None:
    """Return the per-run output folder path when file output is enabled, else ``None``."""
    if not settings.save_run_logs:
        return None
    return resolve_output_run_dir(settings, run_id)


def expected_run_log_file(settings: Settings, run_id: str) -> Path | None:
    """Path to ``run_log.json`` inside the per-run folder (CLI / job hints)."""
    d = expected_run_output_dir(settings, run_id)
    return d / "run_log.json" if d is not None else None


def extract_github_links(
    artifacts: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    """Resolve PR/issue/branch URLs from ``artifacts`` or bus ``message_history``."""
    gh = artifacts.get("github")
    if isinstance(gh, dict) and gh.get("pr_url"):
        return {
            "github_repo": settings.github_repo or None,
            "pr_url": gh.get("pr_url"),
            "issue_url": gh.get("issue_url"),
            "branch": gh.get("branch"),
        }
    for m in artifacts.get("message_history") or []:
        if not isinstance(m, dict):
            continue
        if m.get("from_agent") != "engineer" or m.get("message_type") != "result":
            continue
        p = m.get("payload")
        if not isinstance(p, dict) or not p.get("pr_url"):
            continue
        return {
            "github_repo": settings.github_repo or None,
            "pr_url": p.get("pr_url"),
            "issue_url": p.get("issue_url"),
            "branch": p.get("branch"),
        }
    return {
        "github_repo": settings.github_repo or None,
        "pr_url": None,
        "issue_url": None,
        "branch": None,
    }


def _agent_timelines_and_stats(
    message_history: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Compute per-agent message counts and compact timeline rows."""
    agent_ids = {a["id"] for a in PIPELINE_AGENTS}
    out: dict[str, dict[str, Any]] = {
        aid: {"stats": {"messages_sent": 0, "messages_received": 0}, "timeline": []}
        for aid in agent_ids
    }
    for m in message_history:
        mid = m.get("message_id")
        ts = m.get("timestamp")
        mtype = m.get("message_type")
        fid = m.get("from_agent")
        tid = m.get("to_agent")
        payload = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        pkeys = sorted(payload.keys()) if isinstance(payload, dict) else []
        base = {
            "message_id": mid,
            "timestamp": ts,
            "message_type": mtype,
            "payload_keys": pkeys,
        }
        if fid in out:
            out[fid]["stats"]["messages_sent"] += 1
            out[fid]["timeline"].append({**base, "direction": "out", "peer": tid})
        if tid in out:
            out[tid]["stats"]["messages_received"] += 1
            out[tid]["timeline"].append({**base, "direction": "in", "peer": fid})
    return out


def _agent_outputs(artifacts: dict[str, Any], agent_id: str) -> dict[str, Any]:
    """Pick artifact fragments attributed to one agent."""
    keys = _AGENT_OUTPUT_KEYS.get(agent_id, ())
    return {k: artifacts[k] for k in keys if k in artifacts}


def build_run_log_document(
    *,
    run_id: str,
    idea: str,
    started_at: str,
    finished_at: str,
    status: Literal["completed", "failed"],
    error: str | None,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the JSON structure for ``run_log.json``."""
    message_history = artifacts.get("message_history")
    if not isinstance(message_history, list):
        message_history = []

    timelines = _agent_timelines_and_stats(
        [m for m in message_history if isinstance(m, dict)],
    )

    agents_section: list[dict[str, Any]] = []
    for meta in PIPELINE_AGENTS:
        aid = meta["id"]
        block: dict[str, Any] = {
            "id": aid,
            "title": meta["title"],
            "description": meta["description"],
            **timelines.get(
                aid,
                {"stats": {"messages_sent": 0, "messages_received": 0}, "timeline": []},
            ),
            "outputs": _agent_outputs(artifacts, aid),
        }
        agents_section.append(block)

    errors = artifacts.get("errors")
    if not isinstance(errors, list):
        errors = []

    return {
        "schema_version": 1,
        "run": {
            "id": run_id,
            "idea": idea,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "error": error,
            "errors": errors,
        },
        "agents": agents_section,
        "message_history": message_history,
    }


def _write_links_files(
    run_dir: Path,
    links: dict[str, Any],
    *,
    local_index_saved: bool,
) -> None:
    """Write ``links.json`` and a plain-text ``links.txt`` for quick copy-paste."""
    (run_dir / "links.json").write_text(
        json.dumps(links, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines: list[str] = []
    if links.get("pr_url"):
        lines.append(f"Pull request: {links['pr_url']}")
    if links.get("issue_url"):
        lines.append(f"Issue: {links['issue_url']}")
    if links.get("branch"):
        lines.append(f"Branch: {links['branch']}")
    if links.get("github_repo"):
        lines.append(f"GitHub repo: {links['github_repo']}")
    if local_index_saved:
        lines.append(f"Local landing page (saved copy): {run_dir / 'index.html'}")
    (run_dir / "links.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_run_output(
    settings: Settings,
    *,
    run_id: str,
    idea: str,
    started_at: str,
    finished_at: str,
    status: Literal["completed", "failed"],
    error: str | None,
    artifacts: dict[str, Any],
    html_content: str | None = None,
) -> Path | None:
    """Write ``output/<run_id>/``: ``run_log.json``, ``links.*``, optional ``index.html``.

    Returns:
        Path to the run directory, or ``None`` if persistence is disabled.
    """
    if not settings.save_run_logs:
        return None
    run_dir = resolve_output_run_dir(settings, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    doc = build_run_log_document(
        run_id=run_id,
        idea=idea,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        error=error,
        artifacts=artifacts,
    )
    (run_dir / "run_log.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    links = extract_github_links(artifacts, settings)
    if html_content is not None:
        (run_dir / "index.html").write_text(html_content, encoding="utf-8")
    _write_links_files(run_dir, links, local_index_saved=html_content is not None)

    logger.info("Run output written under %s", run_dir)
    return run_dir

