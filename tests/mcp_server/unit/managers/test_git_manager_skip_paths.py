# tests/mcp_server/unit/managers/test_git_manager_skip_paths.py
"""
Tests for GitManager commit_with_scope() skip_paths forwarding.

Regression guard for skip_paths parameter plumbing: commit_with_scope() must
accept skip_paths and forward it unchanged to GitAdapter.commit().

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.managers.git_manager, mcp_server.config.loader
"""

from pathlib import Path
from unittest.mock import MagicMock

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import GitManager


def _make_manager() -> tuple[GitManager, MagicMock]:
    """Return (manager, mock_adapter) wired up for unit testing."""
    mock_adapter = MagicMock()
    mock_adapter.commit.return_value = "def5678"

    loader = ConfigLoader(Path(".st3/config"))
    git_config = loader.load_git_config()
    workphases_config = loader.load_workphases_config()
    manager = GitManager(
        git_config=git_config, adapter=mock_adapter, workphases_config=workphases_config
    )
    return manager, mock_adapter


class TestGitManagerSkipPaths:
    """Unit tests for skip_paths forwarding in GitManager.commit_with_scope()."""

    def test_commit_with_scope_passes_skip_paths_to_adapter(self) -> None:
        """commit_with_scope() forwards skip_paths to GitAdapter.commit()."""
        manager, mock_adapter = _make_manager()

        skip = frozenset({".st3/state.json"})

        manager.commit_with_scope(
            workflow_phase="implementation",
            message="add feature",
            note_context=NoteContext(),
            sub_phase="green",
            cycle_number=2,
            skip_paths=skip,
        )

        call_kwargs = mock_adapter.commit.call_args
        assert call_kwargs is not None, "GitAdapter.commit() was not called"
        _, kwargs = call_kwargs
        assert "skip_paths" in kwargs, (
            f"skip_paths not forwarded to GitAdapter.commit(). Actual kwargs: {kwargs}"
        )
        assert kwargs["skip_paths"] == skip

    def test_commit_with_scope_skip_paths_default_is_empty_frozenset(self) -> None:
        """When skip_paths omitted, GitAdapter.commit() receives frozenset().

        Verifies backward compatibility: callers without skip_paths see no
        side-effects from the postcondition.
        """
        manager, mock_adapter = _make_manager()

        manager.commit_with_scope(
            workflow_phase="implementation",
            message="normal commit",
            note_context=NoteContext(),
            sub_phase="green",
            cycle_number=2,
        )

        call_kwargs = mock_adapter.commit.call_args
        assert call_kwargs is not None
        _, kwargs = call_kwargs
        assert kwargs.get("skip_paths", frozenset()) == frozenset()
