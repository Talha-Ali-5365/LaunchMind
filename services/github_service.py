"""GitHub REST API (Engineer + QA)."""

from __future__ import annotations

import base64
import logging
import re
from functools import partial
from typing import Any

import requests

from core.settings import Settings
from utils.retry import with_retry

logger = logging.getLogger(__name__)


def _github_http_once(
    url: str,
    headers: dict[str, str],
    method: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> requests.Response:
    """Perform a single GitHub REST request and validate status.

    Args:
        url: Full request URL.
        headers: Request headers including auth.
        method: HTTP verb.
        json_body: Optional JSON body for write methods.
        params: Optional query parameters.

    Returns:
        Successful ``requests.Response``.

    Raises:
        requests.HTTPError: On non-success status codes.
    """
    r = requests.request(
        method,
        url,
        headers=headers,
        json=json_body,
        params=params,
        timeout=120,
    )
    if r.status_code >= 400:
        logger.error(
            "GitHub API %s %s: %s %s",
            method,
            url,
            r.status_code,
            r.text[:500],
        )
    r.raise_for_status()
    return r


class GitHubService:
    """Thin wrapper around ``api.github.com`` for repo operations."""

    def __init__(self, settings: Settings) -> None:
        self._token = settings.github_token
        self._repo = settings.github_repo.strip()
        if "/" not in self._repo:
            raise ValueError("GITHUB_REPO must be owner/name")
        self._headers = {
            "Authorization": f"token {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @property
    def owner_repo(self) -> tuple[str, str]:
        """Return ``(owner, repo_name)`` tuple."""
        o, r = self._repo.split("/", 1)
        return o, r

    def _url(self, path: str) -> str:
        """Build absolute repo URL for a path fragment."""
        o, r = self.owner_repo
        return f"https://api.github.com/repos/{o}/{r}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> requests.Response:
        """Run a retried GitHub HTTP request.

        Args:
            method: HTTP verb.
            path: Path after ``/repos/{owner}/{repo}``.
            json_body: Optional JSON body.
            params: Optional query string parameters.

        Returns:
            Successful response object.
        """
        url = self._url(path)
        return with_retry(
            partial(
                _github_http_once,
                url,
                self._headers,
                method,
                json_body=json_body,
                params=params,
            ),
            operation=f"github.{method}.{path}",
        )

    def get_default_branch(self) -> str:
        """Return the repository default branch name."""
        data = self._request("GET", "").json()
        return str(data.get("default_branch") or "main")

    def get_branch_sha(self, branch: str, *, allow_fallback_to_main: bool = True) -> str:
        """Resolve the SHA for a branch ref.

        Args:
            branch: Branch name (e.g. ``main``, ``agent``).
            allow_fallback_to_main: If False, a missing branch raises instead of falling back to ``main``.
        """
        ref_path = f"/git/ref/heads/{branch}"
        try:
            data = self._request("GET", ref_path).json()
        except requests.HTTPError as e:
            if (
                allow_fallback_to_main
                and e.response is not None
                and e.response.status_code == 404
                and branch != "main"
            ):
                return self.get_branch_sha("main", allow_fallback_to_main=True)
            raise
        return str(data["object"]["sha"])

    def create_branch(self, branch_name: str, from_sha: str) -> None:
        """Create ``refs/heads/{branch_name}`` pointing at ``from_sha``."""
        self._request(
            "POST",
            "/git/refs",
            json_body={"ref": f"refs/heads/{branch_name}", "sha": from_sha},
        )

    def create_issue(self, title: str, body: str) -> dict[str, Any]:
        """Open a new issue; return parsed JSON body."""
        return self._request(
            "POST",
            "/issues",
            json_body={"title": title, "body": body},
        ).json()

    def get_blob_sha_if_exists(self, path: str, branch: str) -> str | None:
        """Return the blob SHA for ``path`` on ``branch``, or None if the file is absent.

        Does not use the retried ``_request`` helper: 404 is expected for first-time
        uploads and must not be retried or logged as a hard failure.
        """
        url = self._url(f"/contents/{path}")
        r = requests.request(
            "GET",
            url,
            headers=self._headers,
            params={"ref": branch},
            timeout=120,
        )
        if r.status_code == 404:
            logger.debug("No existing file at %s on ref=%s (will create)", path, branch)
            return None
        if r.status_code >= 400:
            logger.error(
                "GitHub API GET %s: %s %s",
                url,
                r.status_code,
                r.text[:500],
            )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return None
        sha = data.get("sha")
        return str(sha) if sha else None

    def put_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> dict[str, Any]:
        """Create or update a file on a branch (Contents API)."""
        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        contents_path = f"/contents/{path}"
        sha = self.get_blob_sha_if_exists(path, branch)
        body: dict[str, Any] = {
            "message": message,
            "content": b64,
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        # PRD: commits attributable to the Engineer agent (visible in Git history).
        agent_author = {
            "name": "EngineerAgent",
            "email": "agent@launchmind.ai",
        }
        body["author"] = agent_author
        body["committer"] = agent_author
        return self._request("PUT", contents_path, json_body=body).json()

    def create_pull_request(
        self,
        *,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict[str, Any]:
        """Open a pull request ``head`` -> ``base``."""
        return self._request(
            "POST",
            "/pulls",
            json_body={"title": title, "body": body, "head": head, "base": base},
        ).json()

    def get_pull(self, pull_number: int) -> dict[str, Any]:
        """Fetch pull request metadata JSON."""
        return self._request("GET", f"/pulls/{pull_number}").json()

    def get_file_content(self, path: str, ref: str) -> str:
        """Return decoded UTF-8 file content at ``ref``."""
        data = self._request("GET", f"/contents/{path}", params={"ref": ref}).json()
        if isinstance(data, list):
            raise RuntimeError(f"Path {path} is a directory at {ref}")
        content = data.get("content", "")
        return base64.b64decode(content).decode("utf-8")

    def create_pull_comment(
        self,
        pull_number: int,
        *,
        body: str,
        commit_id: str,
        path: str,
        line: int,
    ) -> dict[str, Any]:
        """Create a single inline review comment on a PR diff."""
        return self._request(
            "POST",
            f"/pulls/{pull_number}/comments",
            json_body={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side": "RIGHT",
            },
        ).json()


def parse_pull_number_from_url(url: str) -> int | None:
    """Extract PR number from a GitHub pull request URL if present."""
    m = re.search(r"/pull/(\d+)", url)
    return int(m.group(1)) if m else None
