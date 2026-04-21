# mcp_server/state/pr_status_cache.py
"""In-memory PR status cache with cold-start GitHub API fallback.

@layer: Backend (State)
@dependencies: [mcp_server.core.interfaces, mcp_server.managers.github_manager]
@responsibilities:
    - Cache PR open/absent status per branch for the current MCP session
    - Fall back to GitHub API on cold start (cache miss)
    - Serve as the single source of truth during an active session
"""

from __future__ import annotations

from mcp_server.core.interfaces import IPRStatusReader, IPRStatusWriter, PRStatus
from mcp_server.managers.github_manager import GitHubManager


class PRStatusCache(IPRStatusReader, IPRStatusWriter):
    """Session-leading in-memory cache for per-branch PR status.

    Lifecycle:
    - cache miss (cold start) → query GitHub API → store in cache
    - active session          → cache is authoritative; no automatic refresh
    - merge_pr (success)      → set_pr_status(branch, PRStatus.ABSENT)
    """

    def __init__(self, github_manager: GitHubManager) -> None:
        self._github = github_manager
        self._cache: dict[str, PRStatus] = {}

    def get_pr_status(self, branch: str) -> PRStatus:
        """Return cached status; fall back to GitHub API on cold start."""
        if branch not in self._cache:
            self._cache[branch] = self._fetch_from_api(branch)
        return self._cache[branch]

    def set_pr_status(self, branch: str, status: PRStatus) -> None:
        """Write *status* for *branch* into the session cache."""
        self._cache[branch] = status

    def _fetch_from_api(self, branch: str) -> PRStatus:
        """Query GitHub API for the current PR status of *branch*."""
        return self._github.get_pr_status(branch)
