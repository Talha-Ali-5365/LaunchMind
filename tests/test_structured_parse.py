"""LangChain structured parse + fence fallback."""

from pydantic import BaseModel

from utils.json_extract import extract_json_object
from utils.structured_parse import parse_structured_llm_json


class _SampleModel(BaseModel):
    ok: bool
    n: int


def test_extract_json_object_fence() -> None:
    text = """Here:
```json
{"ok": true, "n": 1}
```
"""
    assert extract_json_object(text) == {"ok": True, "n": 1}


def test_parse_structured_llm_json_fence() -> None:
    text = """```json
{"ok": true, "n": 42}
```"""
    out = parse_structured_llm_json(text, _SampleModel)
    assert out == {"ok": True, "n": 42}
