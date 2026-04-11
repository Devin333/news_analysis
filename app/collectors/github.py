"""GitHub Collector using GitHub API."""

import hashlib
import time
from datetime import datetime
from typing import Any

import httpx

from app.bootstrap.logging import get_logger
from app.collectors.base import BaseCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult, RawCollectedItem

logger = get_logger(__name__)


class GitHubCollector(BaseCollector):
    """Collector for GitHub repositories, issues, and releases via API.

    Supports fetching:
    - Repository releases
    - Repository issues
    - Repository commits (recent)
    - Trending repositories (via search)
    """

    API_BASE = "https://api.github.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize GitHubCollector.

        Args:
            token: GitHub personal access token for higher rate limits.
            timeout: HTTP request timeout in seconds.
        """
        self._token = token
        self._timeout = timeout

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.GITHUB]

    async def validate(self, request: CollectRequest) -> str | None:
        """Validate that base_url contains repo info."""
        base_error = await super().validate(request)
        if base_error:
            return base_error
        if not request.base_url:
            return "GitHub collector requires base_url (e.g., owner/repo)"
        return None

    async def collect(self, request: CollectRequest) -> CollectResult:
        """Fetch GitHub data based on request configuration."""
        start = time.monotonic()
        base_url = request.base_url

        if not base_url:
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error="base_url is required",
                duration_seconds=time.monotonic() - start,
            )

        # Determine collection mode from metadata
        mode = request.metadata_json.get("mode", "releases")
        repo = base_url.strip("/")

        logger.info(f"Fetching GitHub {mode} for {repo}")

        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=headers,
                follow_redirects=True,
            ) as client:
                if mode == "releases":
                    items = await self._fetch_releases(client, repo, request.max_items)
                elif mode == "issues":
                    items = await self._fetch_issues(client, repo, request.max_items)
                elif mode == "commits":
                    items = await self._fetch_commits(client, repo, request.max_items)
                elif mode == "trending":
                    items = await self._fetch_trending(client, request.max_items)
                else:
                    items = await self._fetch_releases(client, repo, request.max_items)

            return CollectResult(
                source_id=request.source_id,
                success=True,
                items=items,
                duration_seconds=time.monotonic() - start,
                metadata={"repo": repo, "mode": mode},
            )

        except httpx.HTTPStatusError as exc:
            logger.error(f"GitHub API error: {exc.response.status_code}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=f"GitHub API error: {exc.response.status_code}",
                duration_seconds=time.monotonic() - start,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"GitHub collection failed: {exc}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with optional auth."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _fetch_releases(
        self, client: httpx.AsyncClient, repo: str, max_items: int
    ) -> list[RawCollectedItem]:
        """Fetch repository releases."""
        url = f"{self.API_BASE}/repos/{repo}/releases"
        response = await client.get(url, params={"per_page": min(max_items, 100)})
        response.raise_for_status()
        releases = response.json()

        items: list[RawCollectedItem] = []
        for release in releases[:max_items]:
            items.append(
                RawCollectedItem(
                    external_id=str(release["id"]),
                    url=release["html_url"],
                    title=release.get("name") or release["tag_name"],
                    raw_text=release.get("body", ""),
                    raw_json=release,
                    published_at=self._parse_date(release.get("published_at")),
                    author=release.get("author", {}).get("login"),
                    extra={"tag": release["tag_name"], "type": "release"},
                )
            )
        return items

    async def _fetch_issues(
        self, client: httpx.AsyncClient, repo: str, max_items: int
    ) -> list[RawCollectedItem]:
        """Fetch repository issues."""
        url = f"{self.API_BASE}/repos/{repo}/issues"
        response = await client.get(
            url, params={"per_page": min(max_items, 100), "state": "all", "sort": "updated"}
        )
        response.raise_for_status()
        issues = response.json()

        items: list[RawCollectedItem] = []
        for issue in issues[:max_items]:
            # Skip pull requests (they appear in issues endpoint)
            if "pull_request" in issue:
                continue
            items.append(
                RawCollectedItem(
                    external_id=str(issue["id"]),
                    url=issue["html_url"],
                    title=issue["title"],
                    raw_text=issue.get("body", ""),
                    raw_json=issue,
                    published_at=self._parse_date(issue.get("created_at")),
                    author=issue.get("user", {}).get("login"),
                    extra={
                        "number": issue["number"],
                        "state": issue["state"],
                        "labels": [l["name"] for l in issue.get("labels", [])],
                        "type": "issue",
                    },
                )
            )
        return items

    async def _fetch_commits(
        self, client: httpx.AsyncClient, repo: str, max_items: int
    ) -> list[RawCollectedItem]:
        """Fetch recent commits."""
        url = f"{self.API_BASE}/repos/{repo}/commits"
        response = await client.get(url, params={"per_page": min(max_items, 100)})
        response.raise_for_status()
        commits = response.json()

        items: list[RawCollectedItem] = []
        for commit in commits[:max_items]:
            commit_data = commit.get("commit", {})
            items.append(
                RawCollectedItem(
                    external_id=commit["sha"],
                    url=commit["html_url"],
                    title=commit_data.get("message", "").split("\n")[0],
                    raw_text=commit_data.get("message", ""),
                    raw_json=commit,
                    published_at=self._parse_date(
                        commit_data.get("author", {}).get("date")
                    ),
                    author=commit.get("author", {}).get("login")
                    or commit_data.get("author", {}).get("name"),
                    extra={"sha": commit["sha"][:7], "type": "commit"},
                )
            )
        return items

    async def _fetch_trending(
        self, client: httpx.AsyncClient, max_items: int
    ) -> list[RawCollectedItem]:
        """Fetch trending repositories via search API."""
        url = f"{self.API_BASE}/search/repositories"
        response = await client.get(
            url,
            params={
                "q": "stars:>1000 pushed:>2026-01-01",
                "sort": "stars",
                "order": "desc",
                "per_page": min(max_items, 100),
            },
        )
        response.raise_for_status()
        data = response.json()

        items: list[RawCollectedItem] = []
        for repo in data.get("items", [])[:max_items]:
            items.append(
                RawCollectedItem(
                    external_id=str(repo["id"]),
                    url=repo["html_url"],
                    title=repo["full_name"],
                    raw_text=repo.get("description", ""),
                    raw_json=repo,
                    published_at=self._parse_date(repo.get("created_at")),
                    author=repo.get("owner", {}).get("login"),
                    extra={
                        "stars": repo["stargazers_count"],
                        "forks": repo["forks_count"],
                        "language": repo.get("language"),
                        "type": "repository",
                    },
                )
            )
        return items

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parse ISO date string."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None
