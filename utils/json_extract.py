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

    depth = 0
    end = -1
    for i, ch in enumerate(s[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise ValueError("Unbalanced JSON braces in model output")

    return json.loads(s[start:end])
