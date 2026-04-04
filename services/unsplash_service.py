"""Unsplash API: search photos for engineer landing pages (hotlink + attribution)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from core.settings import Settings

logger = logging.getLogger(__name__)

_UNSPLASH_API = "https://api.unsplash.com"


def _trigger_download(download_location: str, access_key: str) -> None:
    """Notify Unsplash when a photo is used (API guideline)."""
    try:
        requests.get(
            download_location,
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=15,
        )
    except Exception as exc:
        logger.debug("Unsplash download_location ping failed: %s", exc)


def search_photos(
    settings: Settings,
    *,
    query: str,
    per_page: int = 6,
) -> list[dict[str, Any]]:
    """Search Unsplash and return image rows with URLs and attribution metadata.

    Args:
        settings: Must include ``unsplash_access_key`` (Client-ID).
        query: Search query (e.g. ``restaurant kitchen``, ``freelancer laptop``).
        per_page: Number of results (capped at 10 for tool use).

    Returns:
        List of dicts with ``url``, ``alt_suggestion``, ``photographer``,
        ``photographer_url``, ``photo_page``. Empty list if no access key or no results.

    Raises:
        requests.HTTPError: On HTTP errors from the API.
    """
    access = (settings.unsplash_access_key or "").strip()
    if not access:
        return []

    per_page = max(1, min(int(per_page), 10))
    r = requests.get(
        f"{_UNSPLASH_API}/search/photos",
        params={"query": query.strip(), "per_page": per_page},
        headers={"Authorization": f"Client-ID {access}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    results: list[dict[str, Any]] = []

    for item in data.get("results") or []:
        urls = item.get("urls") or {}
        base = urls.get("regular") or urls.get("small") or ""
        if not base:
            continue
        sep = "&" if "?" in base else "?"
        img_url = f"{base}{sep}auto=format&fit=crop&w=1200&q=80"

        user = item.get("user") or {}
        user_links = user.get("links") or {}
        links = item.get("links") or {}
        dl = links.get("download_location")
        if isinstance(dl, str):
            _trigger_download(dl, access)

        desc = item.get("description") or item.get("alt_description") or query
        results.append(
            {
                "url": img_url,
                "alt_suggestion": (desc or query)[:200],
                "photographer": user.get("name") or "Unknown",
                "photographer_url": user_links.get("html") or "https://unsplash.com",
                "photo_page": links.get("html") or "",
            }
        )
        if len(results) >= per_page:
            break

    return results
