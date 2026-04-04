"""Application settings from environment variables."""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.4-mini"

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

    # Per-run folder under repo root: run_log.json, links.json, index.html (see services/run_log.py).
    output_dir: str = "output"
    save_run_logs: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached ``Settings`` (loads ``.env`` on first use via model config)."""
    return Settings()
