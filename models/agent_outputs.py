"""Pydantic models for LangChain structured JSON parsing of agent replies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CEODecomposeProductTask(BaseModel):
    """Focus string delegated to the Product agent."""

    focus: str = ""


class CEODecomposeOut(BaseModel):
    """CEO idea decomposition payload."""

    model_config = ConfigDict(extra="allow")

    product_task: CEODecomposeProductTask = Field(default_factory=CEODecomposeProductTask)
    engineer_hint: str = ""
    marketing_hint: str = ""
    rationale: str = ""


class CEOReviewProductOut(BaseModel):
    """CEO review of the Product specification."""

    acceptable: bool = False
    feedback: str = ""
    missing_or_weak: list[str] = Field(default_factory=list)


class CEOReviewEngineerOut(BaseModel):
    """CEO review of engineering output summary."""

    acceptable: bool = True
    feedback: str = ""


class CEOReviewQAOut(BaseModel):
    """CEO review of the QA report and escalation hint."""

    acceptable: bool = True
    feedback: str = ""
    escalate_to: Literal["engineer", "marketing", "none"] = "engineer"

    @field_validator("escalate_to", mode="before")
    @classmethod
    def _normalize_escalate(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class ProductPersona(BaseModel):
    """Single user persona."""

    name: str
    role: str
    pain_point: str


class ProductFeature(BaseModel):
    """Prioritized feature line item."""

    name: str
    description: str
    priority: int = 1


class ProductSpecOut(BaseModel):
    """Full product spec from the Product agent."""

    value_proposition: str
    personas: list[ProductPersona] = Field(default_factory=list)
    features: list[ProductFeature] = Field(default_factory=list)
    user_stories: list[str] = Field(default_factory=list)


class EngineerResultOut(BaseModel):
    """Engineer agent final JSON summary."""

    model_config = ConfigDict(extra="allow")

    issue_url: str = ""
    pr_url: str = ""
    branch: str = ""
    summary: str = ""
    error: str | None = None


class MarketingCopyOut(BaseModel):
    """Marketing copy bundle after tools ran."""

    tagline: str = ""
    landing_description: str = ""
    cold_email_subject: str = ""
    cold_email_html: str = ""
    social_twitter: str = ""
    social_linkedin: str = ""
    social_instagram: str = ""


class QAReportOut(BaseModel):
    """QA verdict and assessments."""

    model_config = ConfigDict(extra="allow")

    verdict: Literal["pass", "fail"] = "fail"
    issues: list[str] = Field(default_factory=list)
    html_assessment: str = ""
    marketing_assessment: str = ""

    @field_validator("verdict", mode="before")
    @classmethod
    def _normalize_verdict(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v
