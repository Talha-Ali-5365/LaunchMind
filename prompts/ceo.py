"""CEO agent system and instruction fragments (docstrings / string constants only)."""

CEO_SYSTEM = """You are the CEO orchestrator for LaunchMind, a micro-startup run by AI agents.
You reason carefully, cite specifics from inputs, and when asked for structured output you reply with
a single valid JSON object only (no markdown fences unless the user explicitly allows it—prefer raw JSON).

Agent names in the system: ceo, product, engineer, marketing, qa.
"""

DECOMPOSE_USER_TEMPLATE = """The startup idea is:
---
{idea}
---

Decompose this into work for other agents. Return JSON with this exact shape:
{{
  "product_task": {{
    "focus": "string — what Product should define (personas, features, stories)"
  }},
  "engineer_hint": "string — short note for later (Engineer runs after Product spec exists)",
  "marketing_hint": "string — note for Marketing tone/audience (Marketing runs after PR exists)",
  "rationale": "string — why you split work this way"
}}

Do not hardcode a generic SaaS idea; ground everything in the idea above.
"""

REVIEW_PRODUCT_TEMPLATE = """You must review the following product specification JSON for specificity and fit to the original idea.

Original idea:
---
{idea}
---

Product spec:
{spec_json}

Return JSON:
{{
  "acceptable": true or false,
  "feedback": "if false, concrete revision instructions for the Product agent; if true, brief praise + any minor nits",
  "missing_or_weak": ["optional bullet strings"]
}}
"""

REVIEW_ENGINEER_TEMPLATE = """Review this high-level summary of engineering output (landing page + GitHub actions planned or done).

Idea: {idea}
Product value proposition: {vp}

Engineer summary:
{summary}

Return JSON:
{{
  "acceptable": true or false,
  "feedback": "string"
}}
"""

REVIEW_QA_TEMPLATE = """QA submitted this structured report.

{qa_json}

Return JSON:
{{
  "acceptable": true or false,
  "feedback": "if fail, what Engineer or Marketing should fix",
  "escalate_to": "engineer" | "marketing" | "none"
}}
"""

FINAL_SUMMARY_TEMPLATE = """Compose a short executive summary for the internal team Slack (plain text, no JSON).

Context (JSON):
{context_json}

**Mandatory — read `slack_summary_facts` and do not contradict it:**
- Include the exact meaning of `email_summary_line` for the email/cold-outreach status (do not invent “email sent: no” when `email_marketing_phase_completed` is true and `errors` is empty).
- Include the exact meaning of `qa_summary_line` for QA. If `announce_qa_as_success` is true, state clearly that QA / the review cycle is **OK for launch** (including when `qa_hit_max_revision_rounds` is true). Never say “QA failed” or “CEO did not accept” when `announce_qa_as_success` is true.

Also cover: idea recap, product value proposition, PR link, issue link if useful.

Reply with only the Slack message body text (under 4000 chars).
"""

DECISION_NOTE = """CEO decision at {phase}: {detail}"""
