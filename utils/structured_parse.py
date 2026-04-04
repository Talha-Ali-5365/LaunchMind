"""Parse agent final-message text with LangChain structured output parsers.

Uses ``JsonOutputParser`` from ``langchain_core.output_parsers`` (see LangChain structured
output / output parsers in the LangChain docs). When the model wraps JSON in prose or
markdown, ``JsonOutputParser`` may fail; we then fall back to brace extraction plus
Pydantic validation.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

from utils.json_extract import extract_json_object

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def parse_structured_llm_json(text: str, model_cls: type[T]) -> dict[str, Any]:
    """Turn raw LLM text into a JSON-ready dict using a LangChain parser + Pydantic schema.

    Primary path: `JsonOutputParser(pydantic_object=...)` from LangChain Core, which parses
    JSON and validates against the given Pydantic model (see
    https://docs.langchain.com/oss/python/langchain/structured-output for structured
    output concepts).

    Fallback: if parsing fails (e.g. extra prose around the object), extract the first
    balanced ``{...}`` block (and optional ``` fences) then ``model_cls.model_validate``.

    Args:
        text: Raw assistant text (often the last message from a Deep Agent).
        model_cls: Pydantic model class for the expected JSON shape.

    Returns:
        Validated data as plain dict (JSON-serializable values).

    Raises:
        ValueError: If both the LangChain parser and the fallback path fail validation.
    """
    parser = JsonOutputParser(pydantic_object=model_cls)
    try:
        parsed = parser.parse(text.strip())
        if isinstance(parsed, BaseModel):
            return parsed.model_dump(mode="json")
        return model_cls.model_validate(parsed).model_dump(mode="json")
    except Exception as first_err:
        logger.debug("JsonOutputParser failed, using brace fallback: %s", first_err)
        try:
            raw = extract_json_object(text)
            validated = model_cls.model_validate(raw)
            return validated.model_dump(mode="json")
        except Exception as second_err:
            raise ValueError(
                f"Structured parse failed: {first_err!s}; fallback: {second_err!s}"
            ) from second_err
