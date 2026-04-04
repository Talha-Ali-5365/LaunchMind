# LaunchMind

Multi-agent system that takes a startup **idea** and runs a micro-startup workflow: **Product** spec, **Engineer** landing page + real **GitHub** issue/branch/PR, **Marketing** cold email (**Resend**) + **Slack** Block Kit post (PR URL comes from the **CEO** only), **QA** inline PR comments, **CEO** orchestration with LLM reviews and multiple revision loops, and a final CEO summary to Slack.

Built with **FastAPI**, **LangChain Deep Agents** ([quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart)), and **OpenAI-compatible** chat (`langchain-openai` `ChatOpenAI`, e.g. Metaminds `base_url`).

## Startup idea
- TBD

## Repository layout

| Path | Role |
|------|------|
| `main.py` | FastAPI `app`, `POST /runs`, `GET /runs/{job_id}`, and CLI demo |
| `message_bus.py` | PRD shim re-exporting `MessageBus` |
| `core/` | Settings, `MessageBus` implementation |
| `models/` | Pydantic models: bus messages (`messages.py`), agent JSON shapes (`agent_outputs.py`) |
| `services/pipeline.py` | Phase machine (ordering + CEO reviews) |
| `services/jobs.py` | In-memory job store |
| `services/run_log.py` | Per-run ``output/<id>/`` bundle (log, links, ``index.html``) |
| `services/github_service.py`, `slack_service.py`, `email_service.py`, `unsplash_service.py` | Integrations |
| `agents/` | One Deep Agent builder per role |
| `prompts/` | Prompt strings only |

## Setup

1. Python 3.11+
2. Create a virtualenv and install:

```bash
cd LaunchMind
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

3. Copy `.env.example` → `.env` and fill in real values (never commit `.env`).


4. **Slack**: Bot token with `chat:write`, `channels:read`, `channels:join`; channel `#launches`; invite the bot.

5. **Resend**: API key; with `onboarding@resend.dev`, **`TO_EMAIL` must be the same address as your Resend account** (testing restriction). To mail arbitrary inboxes, [verify a domain](https://resend.com/domains) and set `FROM_EMAIL` to an address on that domain.

6. **Unsplash** (optional, for engineer landing imagery): [Create an application](https://unsplash.com/oauth/applications), copy the **Access Key** into `UNSPLASH_ACCESS_KEY`. The engineer agent calls `search_unsplash_photos`; without a key it falls back to fixed reference URLs in the prompt. `UNSPLASH_SECRET_KEY` and `UNSPLASH_APPLICATION_ID` are optional (dashboard metadata / future OAuth).

## Run

**CLI:**

```bash
python3 main.py "Your startup idea here"
```

**HTTP API (async job):**

```bash
python3 main.py serve
# elsewhere:
curl -s -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" \
  -d '{"idea":"Your startup idea"}'
curl -s http://127.0.0.1:8000/runs/<job_id>
```

## Platforms

| Platform | What agents do |
|----------|----------------|
| GitHub | Issue “Initial landing page”, branch, `index.html` commit, open PR; QA inline comments on HTML |
| Slack | Marketing launch blocks; CEO final summary |
| Resend | Cold outreach to `TO_EMAIL`  |
| Unsplash | Engineer searches photos by query; hotlinks + attribution in HTML |
