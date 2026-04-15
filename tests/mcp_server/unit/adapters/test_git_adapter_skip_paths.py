# tests/mcp_server/unit/adapters/test_git_adapter_skip_paths.py
"""Tests for GitAdapter commit() skip_paths postcondition.

Regression guard for the skip_paths zero-delta contract: every path in
skip_paths must produce zero delta in the resulting commit.

Real-repo integration tests (TestGitAdapterSkipPathsIntegration): the
zero-delta postcondition is proven by inspecting commit.diff(parent) on an
actual git repository.

The interface-contract (mock-ordering) tests were removed in C10 per D5:
§14 violation — tests coupled to implementation mechanism, not contract.

@layer: Tests (Integration)
@dependencies: [pytest, git (GitPython), mcp_server.adapters.git_adapter]
"""

from pathlib import Path

from git import Repo as GitRepo

from mcp_server.adapters.git_adapter import GitAdapter


class TestGitAdapterSkipPathsIntegration:
    """Integration tests using a real git repository.

    Prove the zero-delta postcondition by inspecting commit.diff(parent) on an
    actual git repository. These tests verify the production invariant directly —
    that skip_path produces no change in the committed tree.

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
