"""Slack Web API (Block Kit)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from core.settings import Settings

logger = logging.getLogger(__name__)

# Slack Web API error codes that will not succeed on retry (fix token, scopes, or channel).
_SLACK_NON_RETRYABLE = frozenset(
    {
        "invalid_auth",
        "not_authed",
        "account_inactive",
        "token_revoked",
        "missing_scope",
        "invalid_auth_deprecated",
        "channel_not_found",
        "not_in_channel",
        "is_archived",
    }
)


def _slack_post_json(token: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST ``chat.postMessage`` once and validate ``ok`` flag.

    Args:
        token: Bot OAuth token (``xoxb-...``).
        payload: Slack API JSON body.

    Returns:
        Parsed JSON response dict.

    Raises:
        RuntimeError: If Slack returns ``ok: false``.
        requests.HTTPError: On transport errors.
    """
    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        err = str(data.get("error", "slack_post_failed"))
        logger.error("Slack error: %s", data)
        if err in _SLACK_NON_RETRYABLE:
            logger.error(
                "Slack auth/config error %r — check SLACK_BOT_TOKEN (xoxb- from your app), "
                "app is installed to the workspace, and scopes include chat:write; "
                "invite the bot to the channel or set SLACK_DISABLED=true to skip Slack.",
                err,
            )
        raise RuntimeError(err)
    return data


def _slack_post_once(token: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Single ``chat.postMessage`` attempt (no pointless retries on auth errors)."""
    return _slack_post_json(token, payload)


def post_launch_blocks(
    settings: Settings,
    *,
    tagline: str,
    description: str,
    pr_url: str,
    extra_header: str | None = None,
) -> dict[str, Any]:
    """Post marketing launch blocks to the configured channel.

    Args:
        settings: Application settings (token, channel).
        tagline: Short headline for the header block.
        description: Mrkdwn body for a section block.
        pr_url: Link target for the PR field.
        extra_header: Optional override for header plain text.

    Returns:
        Slack API response dict, or ``{"ok": True, "skipped": True}`` when Slack is disabled.
    """
    if settings.slack_disabled or not (settings.slack_bot_token or "").strip():
        logger.warning(
            "Slack launch post skipped (slack_disabled or empty SLACK_BOT_TOKEN).",
        )
        return {"ok": True, "skipped": True}

    header_text = extra_header or f"New Launch: {tagline}"
    payload: dict[str, Any] = {
        "channel": settings.slack_channel,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header_text[:150]},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": description},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View PR>"},
                    {"type": "mrkdwn", "text": "*Status:* Ready for review"},
                ],
            },
        ],
    }
    try:
        return _slack_post_once(settings.slack_bot_token, payload)
    except RuntimeError as e:
        code = str(e)
        if code in _SLACK_NON_RETRYABLE:
            logger.warning(
                "Slack launch post skipped (permanent error %r). "
                "Fix the token or set SLACK_DISABLED=true.",
                code,
            )
            return {"ok": True, "skipped": True, "slack_error": code}
        raise


def post_ceo_team_summary(settings: Settings, text: str) -> dict[str, Any]:
    """Post the final CEO summary as Block Kit to Slack.

    Args:
        settings: Application settings.
        text: Mrkdwn-capable summary body (truncated for API limits).

    Returns:
        Slack API response dict, or ``{"ok": True, "skipped": True}`` when Slack is disabled.
    """
    if settings.slack_disabled or not (settings.slack_bot_token or "").strip():
        logger.warning(
            "Slack CEO summary skipped (slack_disabled or empty SLACK_BOT_TOKEN).",
        )
        return {"ok": True, "skipped": True}

    payload: dict[str, Any] = {
        "channel": settings.slack_channel,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "LaunchMind — CEO summary"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text[:2900]},
            },
        ],
    }
    try:
        return _slack_post_once(settings.slack_bot_token, payload)
    except RuntimeError as e:
        code = str(e)
        if code in _SLACK_NON_RETRYABLE:
            logger.warning(
                "Slack CEO summary skipped (permanent error %r). "
                "Fix the token or set SLACK_DISABLED=true.",
                code,
            )
            return {"ok": True, "skipped": True, "slack_error": code}
        raise
