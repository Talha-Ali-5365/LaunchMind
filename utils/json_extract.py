from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first top-level JSON object from free-form LLM text.

    Strips optional ``` / ```json fences and balances braces.

    Args:
        text: Raw assistant output.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no JSON object can be located or braces are unbalanced.
    """
    if not text or not text.strip():
        raise ValueError("Empty model output")

    s = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
    if fence:
        s = fence.group(1).strip()

    start = s.find("{")
    if start < 0:
        raise ValueError("No JSON object found in model output")

    decoder = json.JSONDecoder()
    try:
        obj, _end = decoder.raw_decode(s, start)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in model output: {e}") from e
    if not isinstance(obj, dict):
        raise ValueError("First JSON value is not an object")
    return obj
