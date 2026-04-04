"""LaunchMind: FastAPI job API + synchronous CLI demo (`python main.py`)."""

from __future__ import annotations

import sys
import threading
import uuid
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()

from core.settings import get_settings
from services.jobs import get_job_store, run_job_thread
from services.pipeline import run_pipeline_for_job, run_pipeline_sync
from services.run_log import expected_run_log_file, expected_run_output_dir

app = FastAPI(title="LaunchMind", version="0.1.0")


class RunRequest(BaseModel):
    idea: str = Field(..., min_length=3, description="Startup idea (plain text)")


@app.post("/runs", status_code=202)
def create_run(body: RunRequest) -> JSONResponse:
    """Start a background pipeline job for the given idea.

    Args:
        body: JSON body with ``idea`` string.

    Returns:
        202 response with ``job_id``.
    """
    store = get_job_store()
    jid = store.create(body.idea)
    threading.Thread(
        target=run_job_thread,
        args=(jid, body.idea, run_pipeline_for_job),
        daemon=True,
    ).start()
    return JSONResponse({"job_id": jid}, status_code=202)


@app.get("/runs/{job_id}")
def get_run(job_id: str) -> dict[str, Any]:
    """Poll job status and optional truncated result payload.

    Args:
        job_id: UUID returned from ``POST /runs``.

    Returns:
        Job metadata and result when complete.

    Raises:
        HTTPException: 404 if the job id is unknown.
    """
    store = get_job_store()
    rec = store.get(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="job not found")
    out: dict[str, Any] = {
        "job_id": rec.job_id,
        "status": rec.status,
        "idea": rec.idea,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
        "error": rec.error,
    }
    if rec.result is not None:
        r = dict(rec.result)
        hist = r.get("message_history")
        if isinstance(hist, list) and len(hist) > 80:
            r["message_history"] = hist[:80]
            r["message_history_truncated"] = True
        out["result"] = r
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("serve", "--serve", "-s"):
        uvicorn.run("main:app", host="0.0.0.0", port=8000)
    else:
        idea = " ".join(sys.argv[1:]).strip() or (
            "A platform where students list second-hand textbooks for sale."
        )
        run_id = str(uuid.uuid4())
        settings = get_settings()
        out_dir = expected_run_output_dir(settings, run_id)
        log_file = expected_run_log_file(settings, run_id)
        print(f"Running pipeline for idea: {idea!r}", flush=True)
        print(f"Run id: {run_id}", flush=True)
        if out_dir is not None:
            print(f"Run output folder: {out_dir}", flush=True)
            if log_file is not None:
                print(
                    "  files: run_log.json, links.json, links.txt, index.html (when available)\n",
                    flush=True,
                )
        try:
            out = run_pipeline_sync(idea, verbose=True, run_id=run_id)
        except Exception:
            if out_dir is not None:
                print(f"\nPartial run output may be under: {out_dir}", flush=True)
            raise
        if out.get("run_output_dir"):
            print(f"\nRun output folder: {out['run_output_dir']}", flush=True)
        if out.get("run_log_path"):
            print(f"Run log: {out['run_log_path']}", flush=True)
        if out.get("landing_page_path"):
            print(f"Landing HTML: {out['landing_page_path']}", flush=True)
