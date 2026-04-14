"""RED tests for GitAdapter.commit() skip_paths postcondition — C2.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.adapters.git_adapter

All tests in this file MUST FAIL before the C2 GREEN changes are implemented.
They become the permanent regression guard for the skip_paths postcondition.
"""

from unittest.mock import MagicMock, patch

from mcp_server.adapters.git_adapter import GitAdapter


class TestGitAdapterSkipPaths:
    """Unit tests for the skip_paths postcondition on GitAdapter.commit()."""

    def _make_adapter(self) -> tuple["GitAdapter", "MagicMock"]:
        """Return (adapter, mock_repo) with a fully patched git Repo."""
        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc1234"
        mock_repo.index.commit.return_value = mock_commit
        adapter = GitAdapter("/fake/path")
        adapter._repo = mock_repo  # bypass lazy-init
        return adapter, mock_repo

    # ------------------------------------------------------------------
    # Test 1 — skip_paths accepted when files=None (stage-all route)
    # ------------------------------------------------------------------

    def test_commit_with_skip_paths_files_none_no_delta(self) -> None:
        """skip_paths path is removed from index after git add . (files=None route).

        RED state: TypeError — commit() does not yet accept skip_paths parameter.
        GREEN state: git restore --staged called for each path in skip_paths.
        """
        adapter, mock_repo = self._make_adapter()

        result = adapter.commit(
            message="test commit",
            skip_paths=frozenset({".st3/state.json"}),
        )

        assert result == "abc1234"
        # git add . MUST have been called (stage-all route)
        mock_repo.git.add.assert_called_once_with(".")
        # postcondition: git restore --staged for the skip_path
        mock_repo.git.restore.assert_called_once_with("--staged", ".st3/state.json")

    # ------------------------------------------------------------------
    # Test 2 — skip_paths accepted when files= is supplied (explicit route)
    # ------------------------------------------------------------------

    def test_commit_with_skip_paths_explicit_files_no_delta(self) -> None:
        """skip_paths path is removed from index even when explicit files= list used.

        RED state: TypeError — commit() does not yet accept skip_paths parameter.
        GREEN state: git restore --staged called for each skip_path after staging.
        """
        adapter, mock_repo = self._make_adapter()

        result = adapter.commit(
            message="explicit files commit",
            files=["src/main.py", "src/utils.py"],
            skip_paths=frozenset({".st3/state.json"}),
        )

        assert result == "abc1234"
        # explicit files staged first
        mock_repo.git.add.assert_called_once_with("src/main.py", "src/utils.py")
        # postcondition: git restore --staged for the skip_path
        mock_repo.git.restore.assert_called_once_with("--staged", ".st3/state.json")

    # ------------------------------------------------------------------
    # Test 3 — no restore call when skip_paths is empty (default)
    # ------------------------------------------------------------------

    def test_commit_without_skip_paths_no_restore_staged(self) -> None:
        """git restore --staged is NOT called when skip_paths=frozenset() (default).

        Verifies the postcondition is a no-op for empty skip_paths,
        protecting existing call-sites from accidental side-effects.
        """
        adapter, mock_repo = self._make_adapter()

        result = adapter.commit(message="normal commit")

        assert result == "abc1234"
        mock_repo.git.add.assert_called_once_with(".")
        # The critical assertion: restore must NOT have been invoked
        mock_repo.git.restore.assert_not_called()

    # ------------------------------------------------------------------
    # Test 4 — multiple skip_paths each get an individual restore call
    # ------------------------------------------------------------------

    def test_commit_with_multiple_skip_paths(self) -> None:
        """Each path in skip_paths receives its own git restore --staged call.

        RED state: TypeError — commit() does not yet accept skip_paths parameter.
        GREEN state: one restore call per path, regardless of count.
        """
        adapter, mock_repo = self._make_adapter()

        skip = frozenset({".st3/state.json", ".st3/deliverables.json"})

        adapter.commit(message="multi skip commit", skip_paths=skip)

        restore_calls = mock_repo.git.restore.call_args_list
        assert len(restore_calls) == 2, f"Expected 2 restore calls, got {len(restore_calls)}"
        # Each call is restore("--staged", path) — extract path args
        actual_paths = {c.args[1] for c in restore_calls}
        expected_paths = {".st3/state.json", ".st3/deliverables.json"}
        assert actual_paths == expected_paths
        # All calls must use --staged flag
        assert all(c.args[0] == "--staged" for c in restore_calls)
