"""Resend outbound mail."""

from __future__ import annotations

import logging
from typing import Any

import resend
from resend.exceptions import ResendError

from core.settings import Settings

logger = logging.getLogger(__name__)


def _resend_send_once(api_key: str, payload: dict[str, Any]) -> None:
    """Send one HTML email via Resend API (single attempt; no retry on policy/validation errors).

    Args:
        api_key: Resend API key (``re_...``).
        payload: ``Emails.send`` params: ``from``, ``to``, ``subject``, ``html``.

    Raises:
        ResendError: When the API rejects the request (wrong recipient, unverified domain, etc.).
    """
    resend.api_key = api_key
    response = resend.Emails.send(payload)
    eid = getattr(response, "id", None) or (
        isinstance(response, dict) and response.get("id")
    )
    if eid:
        logger.debug("Resend email id: %s", eid)


def send_html_email(
    settings: Settings,
    *,
    subject: str,
    html_body: str,
    to_email: str | None = None,
) -> None:
    """Send HTML email through Resend (one attempt per call).

    Resend testing / unverified domains only allow sending to the address tied to your
    Resend account. Set ``TO_EMAIL`` in ``.env`` to that exact address, or verify a
    domain at resend.com and use a ``from`` address on that domain.

    Args:
        settings: Application settings (``resend_api_key``, ``from_email``, ``to_email``).
        subject: Email subject line.
        html_body: HTML body.
        to_email: Override recipient; defaults to ``settings.to_email``.
    """
    to = to_email or settings.to_email
    payload: dict[str, Any] = {
        "from": settings.from_email,
        "to": to,
        "subject": subject,
        "html": html_body,
    }
    try:
        _resend_send_once(settings.resend_api_key, payload)
    except ResendError as e:
        logger.error(
            "Resend rejected email (to=%s from=%s): %s. "
            "If you use onboarding@resend.dev, set TO_EMAIL to your Resend login email, "
            "or verify a domain and use a matching from address.",
            to,
            settings.from_email,
            e,
        )
        raise
