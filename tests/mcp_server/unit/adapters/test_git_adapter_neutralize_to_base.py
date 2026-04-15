# tests/mcp_server/unit/adapters/test_git_adapter_neutralize_to_base.py
"""Real-git unit tests for GitAdapter.neutralize_to_base().

Proves that neutralize_to_base(paths, base) satisfies the Model 1 invariant:

    After the call, for every path in `paths`:
        git diff --name-only MERGE_BASE(HEAD, base)..HEAD -- path
    is empty (once the caller commits the staged changes).

Two path-state variants are covered:
  - Path absent from merge-base tree: removed from index and worktree.
  - Path present in merge-base tree: index and worktree reset to merge-base version.

All tests use a real git repository (no mocks).

Test contract source:
    docs/development/issue283/research-model1-branch-tip-neutralization.md  §D5

@layer: Tests (Unit)
@dependencies: [pytest, git (GitPython), mcp_server.adapters.git_adapter]
"""

from pathlib import Path

import pytest
from git import Repo as GitRepo

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.core.exceptions import ExecutionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_git_user(repo: GitRepo) -> None:
    """Set minimal git identity so test commits succeed."""
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")


def _init_repo_with_initial_commit(repo_dir: Path) -> tuple[GitRepo, str]:
    """Create a bare-minimum real git repo.

    Returns:
        (repo, base_branch_name) — base_branch_name is the active branch after
        init (may be 'main' or 'master' depending on git config).
    """
    repo = GitRepo.init(str(repo_dir))
    _configure_git_user(repo)

    (repo_dir / "normal.py").write_text("# initial\n", encoding="utf-8")
    repo.index.add(["normal.py"])
    repo.index.commit("initial commit")

    return repo, repo.active_branch.name


def _commit_staged(repo: GitRepo, message: str) -> str:
    """Commit whatever is staged and return the new commit sha."""
    return repo.index.commit(message).hexsha


# ---------------------------------------------------------------------------
# Scenario A — path absent from BASE (main scenario for current branch)
# ---------------------------------------------------------------------------


class TestNeutralizeToBaseAbsentPath:
    """Path absent from merge-base tree: must be removed from worktree + index."""

    def _setup_branch_with_artifact(self, tmp_path: Path) -> tuple[GitRepo, str, Path]:
        """Return (repo, base_branch, artifact_file) with artifact committed on feature."""
        repo, base_branch = _init_repo_with_initial_commit(tmp_path)

        repo.create_head("feature/test").checkout()

        artifact = tmp_path / ".st3" / "state.json"
        artifact.parent.mkdir()
        artifact.write_text('{"cycle": 1}', encoding="utf-8")
        repo.index.add([".st3/state.json"])
        repo.index.commit("add artifact on feature branch")

        return repo, base_branch, artifact

    def test_absent_path_removed_from_worktree_after_neutralize(
        self, tmp_path: Path
    ) -> None:
        """Path absent from BASE is removed from worktree after neutralize_to_base().

        git restore --source=MERGE_BASE --staged --worktree restores to
        'absent' state, which deletes the file from the working tree.
        """
        repo, base_branch, artifact = self._setup_branch_with_artifact(tmp_path)

        adapter = GitAdapter(str(tmp_path))
        adapter.neutralize_to_base(frozenset({".st3/state.json"}), base_branch)

        assert not artifact.exists(), (
            "neutralize_to_base must remove path from worktree when absent from merge-base"
        )

    def test_absent_path_removed_from_index_after_neutralize(
        self, tmp_path: Path
    ) -> None:
        """Path absent from BASE is removed from git index after neutralize_to_base()."""
        repo, base_branch, artifact = self._setup_branch_with_artifact(tmp_path)

        adapter = GitAdapter(str(tmp_path))
        adapter.neutralize_to_base(frozenset({".st3/state.json"}), base_branch)

        ls_output = repo.git.ls_files(".st3/state.json")
        assert ls_output == "", (
            f"neutralize_to_base must remove path from index when absent from merge-base. "
            f"ls-files output: {ls_output!r}"
        )

    def test_model1_invariant_absent_path(self, tmp_path: Path) -> None:
        """Model 1 invariant: diff merge_base..HEAD empty after neutralize + commit.

        This is the core contract: after neutralize_to_base() + commit,
        the merge-base diff must be empty for the excluded path.
        """
        repo, base_branch, artifact = self._setup_branch_with_artifact(tmp_path)

        adapter = GitAdapter(str(tmp_path))
        adapter.neutralize_to_base(frozenset({".st3/state.json"}), base_branch)
        _commit_staged(repo, f"chore(P_READY): neutralize branch-local artifacts to '{base_branch}'")

        merge_base_sha = repo.git.merge_base("HEAD", base_branch)
        diff_output = repo.git.diff(
            "--name-only", f"{merge_base_sha}..HEAD", "--", ".st3/state.json"
        )
        assert diff_output == "", (
            f"Model 1 invariant violated: .st3/state.json still appears in diff. "
            f"Diff output: {diff_output!r}"
        )

    def test_normal_file_unaffected_by_neutralize(self, tmp_path: Path) -> None:
        """neutralize_to_base must not touch files outside the paths argument."""
        repo, base_branch, artifact = self._setup_branch_with_artifact(tmp_path)

        normal = tmp_path / "normal.py"
        normal.write_text("# modified\n", encoding="utf-8")
        repo.index.add(["normal.py"])
        repo.index.commit("modify normal.py on feature")

        adapter = GitAdapter(str(tmp_path))
        adapter.neutralize_to_base(frozenset({".st3/state.json"}), base_branch)

        # normal.py still has the modified content — neutralize did not touch it
        assert normal.read_text(encoding="utf-8") == "# modified\n", (
            "neutralize_to_base must not modify files outside the paths argument"
        )


# ---------------------------------------------------------------------------
# Scenario B — path present on BASE (epic-parent scenario)
# ---------------------------------------------------------------------------


class TestNeutralizeToBasePresentPath:
    """Path present in merge-base tree: must be reset to merge-base version."""

    def _setup_epic_parent_scenario(
        self, tmp_path: Path
    ) -> tuple[GitRepo, str, Path, str]:
        """Return (repo, base_branch, artifact_file, base_content).

        BASE branch has its own state.json; child branch overwrites it.
        """
        repo = GitRepo.init(str(tmp_path))
        _configure_git_user(repo)

        base_content = '{"owner": "base"}'
        artifact = tmp_path / ".st3" / "state.json"
        artifact.parent.mkdir()
        artifact.write_text(base_content, encoding="utf-8")
        (tmp_path / "normal.py").write_text("# initial\n", encoding="utf-8")
        repo.index.add(["normal.py", ".st3/state.json"])
        repo.index.commit("initial commit on base (epic parent)")

        base_branch = repo.active_branch.name

        repo.create_head("feature/child").checkout()
        artifact.write_text('{"owner": "child"}', encoding="utf-8")
        repo.index.add([".st3/state.json"])
        repo.index.commit("child branch overwrites state.json")

        return repo, base_branch, artifact, base_content

    def test_present_path_reset_to_base_version_in_worktree(
        self, tmp_path: Path
    ) -> None:
        """Worktree content equals BASE version after neutralize_to_base().

        Epic-parent scenario: the child branch modified the artifact. After
        neutralize_to_base(), the worktree must contain the BASE version.
        """
        repo, base_branch, artifact, base_content = self._setup_epic_parent_scenario(
            tmp_path
        )

        adapter = GitAdapter(str(tmp_path))
        adapter.neutralize_to_base(frozenset({".st3/state.json"}), base_branch)

        actual = artifact.read_text(encoding="utf-8")
        assert actual == base_content, (
            f"Worktree must be reset to BASE version. "
            f"Expected: {base_content!r}, got: {actual!r}"
        )

    def test_model1_invariant_present_path(self, tmp_path: Path) -> None:
        """Model 1 invariant: diff merge_base..HEAD empty after neutralize + commit.

        Epic-parent scenario: after neutralize_to_base() + commit, the
        merge-base diff must be empty for the excluded path.
        """
        repo, base_branch, artifact, base_content = self._setup_epic_parent_scenario(
            tmp_path
        )

        adapter = GitAdapter(str(tmp_path))
        adapter.neutralize_to_base(frozenset({".st3/state.json"}), base_branch)
        _commit_staged(repo, f"chore(P_READY): neutralize branch-local artifacts to '{base_branch}'")

        merge_base_sha = repo.git.merge_base("HEAD", base_branch)
        diff_output = repo.git.diff(
            "--name-only", f"{merge_base_sha}..HEAD", "--", ".st3/state.json"
        )
        assert diff_output == "", (
            f"Model 1 invariant violated (epic-parent scenario): "
            f".st3/state.json still appears in diff. Diff output: {diff_output!r}"
        )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestNeutralizeToBaseErrorHandling:
    """Invalid inputs must raise ExecutionError."""

    def test_invalid_base_raises_execution_error(self, tmp_path: Path) -> None:
        """ExecutionError raised when git merge-base fails (unknown base branch).

        If the supplied base branch does not exist, git merge-base returns a
        non-zero exit code. neutralize_to_base() must raise ExecutionError.
        """
        repo, base_branch = _init_repo_with_initial_commit(tmp_path)
        repo.create_head("feature/test").checkout()

        adapter = GitAdapter(str(tmp_path))
        with pytest.raises(ExecutionError):
            adapter.neutralize_to_base(
                frozenset({".st3/state.json"}),
                "nonexistent-branch",
            )
