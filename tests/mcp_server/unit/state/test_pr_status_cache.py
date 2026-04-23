# tests/mcp_server/unit/state/test_pr_status_cache.py
"""Unit tests for PRStatusCache.

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.state.pr_status_cache, mcp_server.core.interfaces]
"""

from __future__ import annotations

from unittest.mock import MagicMock

from mcp_server.core.interfaces import IPRStatusReader, IPRStatusWriter, PRStatus
from mcp_server.state.pr_status_cache import PRStatusCache


class TestPRStatusCacheContract:
    """PRStatusCache implements IPRStatusReader and IPRStatusWriter."""

    def test_implements_reader(self) -> None:
        assert issubclass(PRStatusCache, IPRStatusReader)

    def test_implements_writer(self) -> None:
        assert issubclass(PRStatusCache, IPRStatusWriter)

    def test_has_get_pr_status(self) -> None:
        assert hasattr(PRStatusCache, "get_pr_status")

    def test_has_set_pr_status(self) -> None:
        assert hasattr(PRStatusCache, "set_pr_status")


class TestPRStatusCacheBehavior:
    """PRStatusCache is session-leading; GitHub API used only on cold start."""

    def _make_cache(self, api_return: PRStatus = PRStatus.ABSENT) -> PRStatusCache:
        mock_github = MagicMock()
        mock_github.get_pr_status.return_value = api_return
        return PRStatusCache(github_manager=mock_github)

    def test_cold_start_unknown_branch_returns_absent(self) -> None:
        cache = self._make_cache(PRStatus.ABSENT)
        assert cache.get_pr_status("feature/unknown") == PRStatus.ABSENT

    def test_cold_start_delegates_to_github_api(self) -> None:
        mock_github = MagicMock()
        mock_github.get_pr_status.return_value = PRStatus.OPEN
        cache = PRStatusCache(github_manager=mock_github)

        result = cache.get_pr_status("feature/with-pr")

        assert result == PRStatus.OPEN
        mock_github.get_pr_status.assert_called_once_with("feature/with-pr")

    def test_set_then_get_returns_cached_value(self) -> None:
        cache = self._make_cache()
        cache.set_pr_status("feature/my-branch", PRStatus.OPEN)

        assert cache.get_pr_status("feature/my-branch") == PRStatus.OPEN

    def test_cache_hit_does_not_call_api(self) -> None:
        mock_github = MagicMock()
        cache = PRStatusCache(github_manager=mock_github)
        cache.set_pr_status("feature/my-branch", PRStatus.OPEN)

        cache.get_pr_status("feature/my-branch")

        mock_github.get_pr_status.assert_not_called()

    def test_set_absent_clears_open_entry(self) -> None:
        cache = self._make_cache()
        cache.set_pr_status("feature/merged", PRStatus.OPEN)
        cache.set_pr_status("feature/merged", PRStatus.ABSENT)

        assert cache.get_pr_status("feature/merged") == PRStatus.ABSENT
