"""Application settings from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root ``.env`` so keys (e.g. ``UNSPLASH_ACCESS_KEY``) load regardless of process cwd.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _REPO_ROOT / ".env"
load_dotenv(_ENV_FILE)

# Role id for per-agent ``OPENAI_MODEL_*`` resolution (same API base URL for all).
AgentLLMRole = Literal["ceo", "product", "engineer", "marketing", "qa"]

_ALL_AGENT_LLM_ROLES: tuple[AgentLLMRole, ...] = (
    "ceo",
    "product",
    "engineer",
    "marketing",
    "qa",
)


def openai_models_by_agent(settings: Settings) -> dict[str, str]:
    """Resolved ``ChatOpenAI`` ``model`` id per pipeline agent (for run logs)."""
    return {role: settings.openai_model_for_agent(role) for role in _ALL_AGENT_LLM_ROLES}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.4-mini"
    # Optional per-agent model ids (OpenAI-compatible ``model`` param only). Empty → ``openai_model``.
    openai_model_ceo: str = ""
    openai_model_product: str = ""
    openai_model_engineer: str = ""
    openai_model_marketing: str = ""
    openai_model_qa: str = ""

    github_token: str = ""
    github_repo: str = ""

    slack_bot_token: str = ""
    slack_channel: str = "#launches"
    # When True, Slack posts are skipped (local dev without a valid xoxb- token).
    slack_disabled: bool = False

    resend_api_key: str = ""
    from_email: str = ""
    to_email: str = ""

    max_revision_rounds: int = 3
    engineer_branch_prefix: str = "agent-landing-page"
    engineer_base_branch: str = "agent"

    # Per-run folder under repo root: run_log.json, links.json, index.html (see services/run_log.py).
    output_dir: str = "output"
    save_run_logs: bool = True

    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""
    unsplash_application_id: str = ""

    def openai_model_for_agent(self, role: AgentLLMRole) -> str:
        """Return the chat ``model`` string for ``role`` (falls back to ``openai_model``)."""
        raw = getattr(self, f"openai_model_{role}", "")
        chosen = (raw or "").strip()
        return chosen or self.openai_model


@lru_cache
def get_settings() -> Settings:
    """Return cached ``Settings`` (loads ``.env`` on first use via model config)."""
    return Settings()
