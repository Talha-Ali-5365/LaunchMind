"""Run log lists resolved ``model`` on each agent block."""

from __future__ import annotations

from core.settings import Settings, openai_models_by_agent
from services.run_log import build_run_log_document


def test_openai_models_by_agent_overrides() -> None:
    s = Settings(
        openai_model="default-model",
        openai_model_ceo="ceo-only",
        openai_model_product="",
        openai_model_engineer="",
        openai_model_marketing="",
        openai_model_qa="qa-only",
    )
    per = openai_models_by_agent(s)
    assert per["ceo"] == "ceo-only"
    assert per["product"] == "default-model"
    assert per["engineer"] == "default-model"
    assert per["marketing"] == "default-model"
    assert per["qa"] == "qa-only"


def test_build_run_log_document_model_per_agent() -> None:
    doc = build_run_log_document(
        run_id="r1",
        idea="idea",
        started_at="t0",
        finished_at="t1",
        status="completed",
        error=None,
        artifacts={
            "message_history": [],
            "errors": [],
            "openai_model_per_agent": {
                "ceo": "m-ceo",
                "product": "m-product",
                "engineer": "m-eng",
                "marketing": "m-mkt",
                "qa": "m-qa",
            },
        },
    )
    by_id = {a["id"]: a for a in doc["agents"]}
    assert by_id["ceo"]["model"] == "m-ceo"
    assert by_id["qa"]["model"] == "m-qa"
