# tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py
"""
Tests for GitAdapter commit() skip_paths postcondition.

Regression guard for the skip_paths zero-delta contract: every path in
skip_paths must produce zero delta in the resulting commit. Two layers of
proof are provided:

1. Interface-contract tests (TestGitAdapterSkipPaths): the ordering invariant
   — git restore --staged after all staging, before index.commit() — is proven
   via mock_repo.method_calls.
2. Real-repo integration tests (TestGitAdapterSkipPathsIntegration): the
   zero-delta postcondition is proven by inspecting commit.diff(parent) on an
   actual git repository.

@layer: Tests (Unit + Integration)
@dependencies: [pytest, git (GitPython), mcp_server.adapters.git_adapter]
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from git import Repo as GitRepo

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


class TestGitAdapterSkipPathsIntegration:
    """Integration tests using a real git repository.

    Prove the zero-delta postcondition by inspecting commit.diff(parent) on an
    actual git repository. These tests verify the production invariant directly —
    that skip_path produces no change in the committed tree — not just the
    ordering proxy established by the mock-based tests above.

    Exit criterion from planning.md C2 REFACTOR:
        after commit(skip_paths={path}), path must not appear in
        commit.diff(commit.parents[0]).
    """

    @staticmethod
    def _init_repo_with_initial_commit(repo_dir: Path) -> GitRepo:
        """Create a real git repo with an initial commit tracking two files."""
        repo = GitRepo.init(str(repo_dir))
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Test")
            cw.set_value("user", "email", "test@example.com")

        normal = repo_dir / "normal.py"
        state_dir = repo_dir / ".st3"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        normal.write_text("# v1\n", encoding="utf-8")
        state_file.write_text('{"cycle": 1}', encoding="utf-8")

        repo.index.add(["normal.py", ".st3/state.json"])
        repo.index.commit("initial commit")
        return repo

    def test_skip_paths_zero_delta_files_none_route(self, tmp_path: Path) -> None:
        """REAL proof, files=None: skip_path absent from commit.diff(parent).

        Verifies that after GitAdapter.commit(skip_paths={path}), the path does
        not appear in commit.diff(commit.parents[0]). Planning.md C2 REFACTOR
        exit criterion: zero-delta postcondition proven via real git repository.
        """
        repo = self._init_repo_with_initial_commit(tmp_path)
        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / ".st3" / "state.json").write_text('{"cycle": 2}', encoding="utf-8")

        adapter = GitAdapter(str(tmp_path))
        sha = adapter.commit(
            message="feature commit",
            skip_paths=frozenset({".st3/state.json"}),
        )

        commit = repo.commit(sha)
        diff_paths = {d.a_path for d in commit.diff(commit.parents[0])}
        assert ".st3/state.json" not in diff_paths, (
            f"skip_path appeared in commit diff — zero-delta violated. "
            f"Changed paths: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths, (
            "normal.py must appear in diff (sanity guard — test setup integrity check)"
        )

    def test_skip_paths_zero_delta_explicit_files_route(self, tmp_path: Path) -> None:
        """REAL proof, explicit files=: skip_path absent from commit.diff(parent).

        Same zero-delta invariant via the explicit-files staging branch. Both
        normal.py and .st3/state.json are passed to files=; skip_paths removes
        state.json from the index before index.commit(), producing zero delta.
        """
        repo = self._init_repo_with_initial_commit(tmp_path)
        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / ".st3" / "state.json").write_text('{"cycle": 2}', encoding="utf-8")

        adapter = GitAdapter(str(tmp_path))
        sha = adapter.commit(
            message="feature commit",
            files=["normal.py", ".st3/state.json"],
            skip_paths=frozenset({".st3/state.json"}),
        )

        commit = repo.commit(sha)
        diff_paths = {d.a_path for d in commit.diff(commit.parents[0])}
        assert ".st3/state.json" not in diff_paths, (
            f"skip_path appeared in commit diff — zero-delta violated. "
            f"Changed paths: {sorted(diff_paths)}"
        )
        assert "normal.py" in diff_paths, (
            "normal.py must appear in diff (sanity guard — test setup integrity check)"
        )
