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

import logging

from mcp_server.core.interfaces import IPRStatusReader, IPRStatusWriter, PRStatus
from mcp_server.managers.github_manager import GitHubManager

logger = logging.getLogger(__name__)


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
        """Query GitHub API for the current PR status of *branch*.

        Falls back to PRStatus.ABSENT when the API is not yet available
        (GitHubManager.get_pr_status stub until C4). This prevents cold-start
        crashes from propagating as unhandled NotImplementedError.
        """
        try:
            return self._github.get_pr_status(branch)
        except NotImplementedError:
            logger.debug(
                "GitHubManager.get_pr_status() not yet implemented (C4); "
                "defaulting to PRStatus.ABSENT for branch '%s'",
                branch,
            )
            return PRStatus.ABSENT
