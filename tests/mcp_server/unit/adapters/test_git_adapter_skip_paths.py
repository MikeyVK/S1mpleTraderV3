# tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py
"""
Tests for GitAdapter commit() skip_paths postcondition.

Regression guard for the skip_paths zero-delta contract: every path in
skip_paths must produce zero delta in the resulting commit. The ordering
invariant — git restore --staged after all staging, before index.commit() —
is proven via mock_repo.method_calls, which excludes magic-method noise.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.adapters.git_adapter
"""

from unittest.mock import MagicMock, call, patch

from mcp_server.adapters.git_adapter import GitAdapter


def _stub_repo() -> MagicMock:
    """Return a configured MagicMock Repo instance for commit() tests."""
    mock_repo = MagicMock()
    mock_commit_obj = MagicMock()
    mock_commit_obj.hexsha = "abc1234"
    mock_repo.index.commit.return_value = mock_commit_obj
    return mock_repo


class TestGitAdapterSkipPaths:
    """Regression tests for the skip_paths zero-delta postcondition."""

    # ------------------------------------------------------------------
    # Mandatory — zero-delta proof, files=None route
    # ------------------------------------------------------------------

    def test_commit_with_skip_paths_files_none_no_delta(self) -> None:
        """Zero-delta: skip_path absent from commit when files=None (stage-all route).

        Invariant: git restore --staged must appear after git add . and before
        index.commit() in the call sequence. method_calls (which excludes magic
        methods like __bool__) proves the ordering without noise from the repo
        property's lazy-init guard.
        """
        mock_repo = _stub_repo()
        with patch("mcp_server.adapters.git_adapter.Repo", return_value=mock_repo):
            adapter = GitAdapter("/fake/path")
            result = adapter.commit(
                message="test commit",
                skip_paths=frozenset({".st3/state.json"}),
            )

        assert result == "abc1234"
        # Zero-delta proof: restore between staging and the index snapshot.
        assert mock_repo.method_calls == [
            call.git.add("."),
            call.git.restore("--staged", ".st3/state.json"),
            call.index.commit("test commit"),
        ]

    # ------------------------------------------------------------------
    # Mandatory — zero-delta proof, explicit files= route
    # ------------------------------------------------------------------

    def test_commit_with_skip_paths_explicit_files_no_delta(self) -> None:
        """Zero-delta: skip_path absent from commit when explicit files= list supplied.

        Invariant: same ordering — restore after explicit staging, before commit.
        Applies regardless of which staging branch is taken.
        """
        mock_repo = _stub_repo()
        with patch("mcp_server.adapters.git_adapter.Repo", return_value=mock_repo):
            adapter = GitAdapter("/fake/path")
            result = adapter.commit(
                message="explicit files commit",
                files=["src/main.py", "src/utils.py"],
                skip_paths=frozenset({".st3/state.json"}),
            )

        assert result == "abc1234"
        assert mock_repo.method_calls == [
            call.git.add("src/main.py", "src/utils.py"),
            call.git.restore("--staged", ".st3/state.json"),
            call.index.commit("explicit files commit"),
        ]

    # ------------------------------------------------------------------
    # Acceptable secondary — no-op guard for empty skip_paths
    # ------------------------------------------------------------------

    def test_commit_without_skip_paths_no_restore_staged(self) -> None:
        """No git restore --staged when skip_paths=frozenset() (the default).

        Protects existing call-sites: normal commits must not trigger any
        restore calls due to the postcondition loop.
        """
        mock_repo = _stub_repo()
        with patch("mcp_server.adapters.git_adapter.Repo", return_value=mock_repo):
            adapter = GitAdapter("/fake/path")
            result = adapter.commit(message="normal commit")

        assert result == "abc1234"
        mock_repo.git.add.assert_called_once_with(".")
        mock_repo.git.restore.assert_not_called()

    # ------------------------------------------------------------------
    # Acceptable secondary — multiple skip_paths loop coverage
    # ------------------------------------------------------------------

    def test_commit_with_multiple_skip_paths(self) -> None:
        """Each path in skip_paths is individually restored before index.commit().

        Production scenario: EnforcementRunner produces ExclusionNote for both
        .st3/state.json and .st3/deliverables.json; both restores must precede
        the commit to guarantee zero delta for all skip_paths.
        """
        mock_repo = _stub_repo()
        with patch("mcp_server.adapters.git_adapter.Repo", return_value=mock_repo):
            adapter = GitAdapter("/fake/path")
            skip = frozenset({".st3/state.json", ".st3/deliverables.json"})
            adapter.commit(message="multi skip commit", skip_paths=skip)

        restore_calls = mock_repo.git.restore.call_args_list
        assert len(restore_calls) == 2, f"Expected 2 restore calls, got {len(restore_calls)}"
        actual_paths = {c.args[1] for c in restore_calls}
        assert actual_paths == {".st3/state.json", ".st3/deliverables.json"}
        assert all(c.args[0] == "--staged" for c in restore_calls)

        # Ordering proof: both restores precede index.commit().
        method_calls = mock_repo.method_calls
        commit_pos = next(i for i, c in enumerate(method_calls) if "index.commit" in str(c))
        restore_positions = [i for i, c in enumerate(method_calls) if "git.restore" in str(c)]
        assert len(restore_positions) == 2
        assert all(rp < commit_pos for rp in restore_positions)
