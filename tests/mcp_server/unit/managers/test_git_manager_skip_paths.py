"""RED tests for GitManager.commit_with_scope() skip_paths forwarding — C2.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.managers.git_manager

Tests verify that commit_with_scope() accepts skip_paths and forwards it to
GitAdapter.commit(). All tests MUST FAIL before the C2 GREEN changes.
"""

from pathlib import Path
from unittest.mock import MagicMock

from mcp_server.config.loader import ConfigLoader
from mcp_server.managers.git_manager import GitManager


def _make_manager() -> tuple["GitManager", "MagicMock"]:
    """Return (manager, mock_adapter) wired up for unit testing."""
    mock_adapter = MagicMock()
    mock_adapter.commit.return_value = "def5678"

    git_config = ConfigLoader(Path(".st3/config")).load_git_config()
    manager = GitManager(git_config=git_config, adapter=mock_adapter)
    return manager, mock_adapter


class TestGitManagerSkipPaths:
    """Unit tests for skip_paths forwarding in GitManager.commit_with_scope()."""

    # ------------------------------------------------------------------
    # Test 1 — skip_paths forwarded to GitAdapter.commit()
    # ------------------------------------------------------------------

    def test_commit_with_scope_passes_skip_paths_to_adapter(self) -> None:
        """commit_with_scope() must forward skip_paths to GitAdapter.commit().

        RED state: TypeError — commit_with_scope() does not yet accept skip_paths.
        GREEN state: GitAdapter.commit() called with skip_paths=frozenset({...}).
        """
        manager, mock_adapter = _make_manager()

        skip = frozenset({".st3/state.json"})

        manager.commit_with_scope(
            workflow_phase="implementation",
            message="add feature",
            sub_phase="green",
            cycle_number=2,
            skip_paths=skip,
        )

        # The adapter must have received skip_paths
        _call_kwargs = mock_adapter.commit.call_args
        assert _call_kwargs is not None, "GitAdapter.commit() was not called"
        _, kwargs = _call_kwargs
        assert "skip_paths" in kwargs, (
            "skip_paths was not forwarded to GitAdapter.commit(). "
            f"Actual kwargs: {kwargs}"
        )
        assert kwargs["skip_paths"] == skip

    # ------------------------------------------------------------------
    # Test 2 — skip_paths defaults to frozenset() when omitted
    # ------------------------------------------------------------------

    def test_commit_with_scope_skip_paths_default_is_empty_frozenset(self) -> None:
        """When skip_paths is omitted, GitAdapter.commit() receives frozenset().

        Verifies backward compatibility: existing callers without skip_paths
        produce no side-effects from the postcondition.
        """
        manager, mock_adapter = _make_manager()

        manager.commit_with_scope(
            workflow_phase="implementation",
            message="normal commit",
            sub_phase="green",
            cycle_number=2,
        )

        _call_kwargs = mock_adapter.commit.call_args
        assert _call_kwargs is not None
        _, kwargs = _call_kwargs
        # After GREEN: skip_paths MUST be present and equal frozenset()
        assert kwargs.get("skip_paths", frozenset()) == frozenset()
