"""In-memory async job store for FastAPI."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from core.settings import get_settings
from services.run_log import expected_run_log_file, expected_run_output_dir


@dataclass
class JobRecord:
    """Snapshot of one pipeline job."""

    job_id: str
    idea: str
    status: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None
    result: dict[str, Any] | None = None


class JobStore:
    """Thread-safe map of job_id to ``JobRecord``."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}

    def create(self, idea: str) -> str:
        """Insert a pending job and return its id.

        Args:
            idea: Startup idea string from the client.

        Returns:
            New UUID string primary key.
        """
        jid = str(uuid.uuid4())
        with self._lock:
            self._jobs[jid] = JobRecord(job_id=jid, idea=idea, status="pending")
        return jid

    def get(self, job_id: str) -> JobRecord | None:
        """Return the record for ``job_id`` if it exists."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Patch fields on an existing job (no-op if id missing).

        Args:
            job_id: Target job id.
            status: Optional new status string.
            error: Optional error message.
            result: Optional completed result dict.
        """
        with self._lock:
            rec = self._jobs.get(job_id)
            if not rec:
                return
            if status is not None:
                rec.status = status
            if error is not None:
                rec.error = error
            if result is not None:
                rec.result = result
            rec.updated_at = time.time()


_store: JobStore | None = None


def get_job_store() -> JobStore:
    """Return the process-wide singleton ``JobStore``."""
    global _store
    if _store is None:
        _store = JobStore()
    return _store


def run_job_thread(
    job_id: str,
    idea: str,
    runner: Callable[[str, str], dict[str, Any]],
) -> None:
    """Worker target: run ``runner(idea, job_id)`` and update job status.

    Args:
        job_id: Job to mark running / completed / failed.
        idea: Pipeline input string.
        runner: Blocking callable taking ``(idea, job_id)`` (e.g. ``run_pipeline_for_job``).
    """
    store = get_job_store()
    store.update(job_id, status="running")
    settings = get_settings()
    out_dir = expected_run_output_dir(settings, job_id)
    log_path = expected_run_log_file(settings, job_id)
    try:
        result = runner(idea, job_id)
        store.update(job_id, status="completed", result=result)
    except Exception as e:
        payload: dict[str, Any] = {"error": str(e)}
        if out_dir is not None:
            payload["run_output_dir"] = str(out_dir)
        if log_path is not None:
            payload["run_log_path"] = str(log_path)
        store.update(job_id, status="failed", error=str(e), result=payload)
