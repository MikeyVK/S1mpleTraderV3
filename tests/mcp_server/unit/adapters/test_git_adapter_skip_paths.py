"""Tests for GitAdapter.commit() skip_paths postcondition — C2.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.adapters.git_adapter

Tests are the permanent regression guard for the skip_paths postcondition.
"""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.adapters.git_adapter import GitAdapter


@pytest.fixture()
def adapter_and_repo() -> Generator[tuple[GitAdapter, MagicMock], None, None]:
    """Yield (adapter, mock_repo) with the git Repo class patched."""
    with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc1234"
        mock_repo.index.commit.return_value = mock_commit
        mock_repo_class.return_value = mock_repo
        adapter = GitAdapter("/fake/path")
        yield adapter, mock_repo


class TestGitAdapterSkipPaths:
    """Unit tests for the skip_paths postcondition on GitAdapter.commit()."""

    # ------------------------------------------------------------------
    # Test 1 — skip_paths accepted when files=None (stage-all route)
    # ------------------------------------------------------------------

    def test_commit_with_skip_paths_files_none_no_delta(
        self, adapter_and_repo: tuple[GitAdapter, MagicMock]
    ) -> None:
        """skip_paths path removed from index after git add . (files=None route)."""
        adapter, mock_repo = adapter_and_repo

        result = adapter.commit(
            message="test commit",
            skip_paths=frozenset({".st3/state.json"}),
        )

        assert result == "abc1234"
        mock_repo.git.add.assert_called_once_with(".")
        mock_repo.git.restore.assert_called_once_with("--staged", ".st3/state.json")

    # ------------------------------------------------------------------
    # Test 2 — skip_paths accepted when files= is supplied (explicit route)
    # ------------------------------------------------------------------

    def test_commit_with_skip_paths_explicit_files_no_delta(
        self, adapter_and_repo: tuple[GitAdapter, MagicMock]
    ) -> None:
        """skip_paths path removed even when explicit files= list is used."""
        adapter, mock_repo = adapter_and_repo

        result = adapter.commit(
            message="explicit files commit",
            files=["src/main.py", "src/utils.py"],
            skip_paths=frozenset({".st3/state.json"}),
        )

        assert result == "abc1234"
        mock_repo.git.add.assert_called_once_with("src/main.py", "src/utils.py")
        mock_repo.git.restore.assert_called_once_with("--staged", ".st3/state.json")

    # ------------------------------------------------------------------
    # Test 3 — no restore call when skip_paths is empty (default)
    # ------------------------------------------------------------------

    def test_commit_without_skip_paths_no_restore_staged(
        self, adapter_and_repo: tuple[GitAdapter, MagicMock]
    ) -> None:
        """git restore --staged not called when skip_paths=frozenset() (default).

        Verifies the postcondition is a no-op for empty skip_paths,
        protecting existing call-sites from accidental side-effects.
        """
        adapter, mock_repo = adapter_and_repo

        result = adapter.commit(message="normal commit")

        assert result == "abc1234"
        mock_repo.git.add.assert_called_once_with(".")
        mock_repo.git.restore.assert_not_called()

    # ------------------------------------------------------------------
    # Test 4 — multiple skip_paths each get an individual restore call
    # ------------------------------------------------------------------

    def test_commit_with_multiple_skip_paths(
        self, adapter_and_repo: tuple[GitAdapter, MagicMock]
    ) -> None:
        """Each path in skip_paths receives its own git restore --staged call."""
        adapter, mock_repo = adapter_and_repo

        skip = frozenset({".st3/state.json", ".st3/deliverables.json"})

        adapter.commit(message="multi skip commit", skip_paths=skip)

        restore_calls = mock_repo.git.restore.call_args_list
        assert len(restore_calls) == 2, f"Expected 2 restore calls, got {len(restore_calls)}"
        actual_paths = {c.args[1] for c in restore_calls}
        expected_paths = {".st3/state.json", ".st3/deliverables.json"}
        assert actual_paths == expected_paths
        assert all(c.args[0] == "--staged" for c in restore_calls)
