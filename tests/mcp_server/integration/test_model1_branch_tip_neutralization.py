# tests/mcp_server/integration/test_model1_branch_tip_neutralization.py
"""Integration tests for Model 1 branch-tip neutralization (issue #283).

End-to-end proof: ExclusionNote → GitCommitTool.execute() → neutralize_to_base
→ commit → zero net delta against merge base for all excluded paths.

Replaces the stale C3 integration tests in test_git_add_commit_ready_phase_c3.py,
which tested the obsolete skip_paths mechanism.

D1 invariant (from research-model1-branch-tip-neutralization.md):
    After a ready-phase commit with ExclusionNote entries present,
    git diff --name-only MERGE_BASE(HEAD, BASE)..HEAD -- <path>
    must be empty for every excluded path.

Three scenarios (D5 test contract):
    Scenario A: excluded path absent from BASE → zero net-diff AND absent from HEAD tree.
    Scenario B: excluded path present on BASE (epic-parent) → restored to BASE version.
    Scenario C: no ExclusionNotes (non-terminal phase) → all files in net-diff normally.

@layer: Tests (Integration)
@dependencies: [json, pathlib, pytest, pytest-asyncio, git (GitPython),
    mcp_server.adapters.git_adapter, mcp_server.config.loader,
    mcp_server.core.operation_notes, mcp_server.managers.git_manager,
    mcp_server.tools.git_tools]
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from git import Repo as GitRepo

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.operation_notes import ExclusionNote, NoteContext
from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.git_tools import GitCommitInput, GitCommitTool

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

_STATE_JSON = ".st3/state.json"
_DELIVERABLES_JSON = ".st3/deliverables.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo_scenario_a(repo_dir: Path) -> GitRepo:
    """Create a repo where BASE (main) does NOT have the excluded path.

    Branch layout after setup:
        main   (commit M: normal.py only)
        └─ feature/test (commit F: + .st3/state.json added)

    The excluded path (.st3/state.json) exists on feature/test but NOT on main.
    Simulates: developer created a branch-local artifact that was never on BASE.
    After neutralize_to_base the artifact must be absent from HEAD tree.
    """
    repo = GitRepo.init(str(repo_dir))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    repo.git.checkout("-b", "main")
    (repo_dir / "normal.py").write_text("# v1\n", encoding="utf-8")
    repo.index.add(["normal.py"])
    repo.index.commit("initial commit")

    repo.git.checkout("-b", "feature/test")

    # Commit state.json on the feature branch (absent from main)
    state_dir = repo_dir / ".st3"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text('{"cycle": 1}', encoding="utf-8")
    repo.index.add([_STATE_JSON])
    repo.index.commit("add branch-local state artifact")

    return repo


def _init_repo_scenario_b(repo_dir: Path) -> GitRepo:
    """Create a repo where BASE (main) already has the excluded path at v1.

    Branch layout after setup:
        main   (commit M: normal.py + .st3/state.json at v1)
        └─ feature/test (forked from M, inherits v1)

    The test must modify .st3/state.json to v2 on the feature branch. After
    neutralize_to_base the file must be restored to the BASE (v1) version.
    Covers the epic-parent scenario where main itself carries the artifact.
    """
    repo = GitRepo.init(str(repo_dir))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    repo.git.checkout("-b", "main")

    state_dir = repo_dir / ".st3"
    state_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "normal.py").write_text("# v1\n", encoding="utf-8")
    (state_dir / "state.json").write_text('{"cycle": 1}', encoding="utf-8")
    repo.index.add(["normal.py", _STATE_JSON])
    repo.index.commit("initial commit")

    repo.git.checkout("-b", "feature/test")
    return repo


def _make_commit_tool(repo_dir: Path) -> GitCommitTool:
    """Build GitCommitTool operating on repo_dir."""
    loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
    git_config = loader.load_git_config()
    manager = GitManager(
        git_config=git_config,
        adapter=GitAdapter(str(repo_dir)),
        workphases_config=loader.load_workphases_config(),
    )
    return GitCommitTool(manager=manager)


def _has_net_diff(repo: GitRepo, path: str, base: str) -> bool:
    """Return True if path has a net delta between merge-base and HEAD."""
    try:
        merge_base_sha = repo.git.merge_base("HEAD", base).strip()
    except Exception:
        return False
    diff_output = repo.git.diff("--name-only", f"{merge_base_sha}..HEAD", "--", path)
    return bool(diff_output.strip())


def _path_in_head_tree(repo: GitRepo, path: str) -> bool:
    """Return True if path exists in the HEAD commit tree."""
    try:
        repo.git.show(f"HEAD:{path}")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# C10 — Model 1 D1 invariant: end-to-end integration proof
# ---------------------------------------------------------------------------


class TestModel1BranchTipNeutralization:
    """End-to-end proof of the Model 1 D1 invariant via a real git repository.

    ExclusionNote entries drive GitCommitTool to call neutralize_to_base before
    committing. After the commit, excluded paths must produce zero net delta
    against the merge base.
    """

    @pytest.mark.asyncio
    async def test_scenario_a_path_absent_from_base_zero_net_diff(self, tmp_path: Path) -> None:
        """Scenario A: excluded path absent from BASE → zero net-diff and absent from HEAD tree.

        Setup:
            - main has no .st3/state.json (artifact never existed on BASE)
            - feature/test added state.json in a prior commit (branch-local artifact)
            - normal.py modified on feature branch
        Proof (D5 contract):
            - After ready-phase commit with ExclusionNote: zero net-diff against main
            - .st3/state.json absent from HEAD tree (neutralized away entirely)
        """
        repo = _init_repo_scenario_a(tmp_path)

        # Simulate further work: update both the excluded path and a normal file
        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / _STATE_JSON).write_text(
            json.dumps({"cycle": 2, "current_phase": "ready"}), encoding="utf-8"
        )

        tool = _make_commit_tool(tmp_path)
        note_ctx = NoteContext()
        note_ctx.produce(ExclusionNote(file_path=_STATE_JSON))

        params = GitCommitInput(
            message="ready phase commit",
            workflow_phase="ready",
            base="main",
        )
        result = await tool.execute(params, note_ctx)

        assert not result.is_error, f"Expected commit success but got: {result}"
        assert not _has_net_diff(repo, _STATE_JSON, "main"), (
            f"D1 invariant violated (Scenario A): '{_STATE_JSON}' has net delta against 'main'"
        )
        assert not _path_in_head_tree(repo, _STATE_JSON), (
            f"Scenario A: '{_STATE_JSON}' must be absent from HEAD tree after neutralization "
            "(path was not on BASE — neutralize must remove it entirely)"
        )
        assert _has_net_diff(repo, "normal.py", "main"), (
            "Sanity guard: 'normal.py' must have net delta against 'main'"
        )

    @pytest.mark.asyncio
    async def test_scenario_b_path_present_on_base_restored_to_base_version(
        self, tmp_path: Path
    ) -> None:
        """Scenario B (epic-parent): path present on BASE is restored to BASE version.

        Setup:
            - main has .st3/state.json at v1 ({"cycle": 1})
            - feature/test modifies it to v2 ({"cycle": 2, "current_phase": "ready"})
            - normal.py also modified
        Proof (D5 contract):
            - After ready-phase commit with ExclusionNote: zero net-diff against main
            - HEAD tree version of .st3/state.json equals BASE version (v1)
        """
        repo = _init_repo_scenario_b(tmp_path)

        # Scenario B: modify the excluded path on the feature branch (v1 → v2)
        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / _STATE_JSON).write_text(
            json.dumps({"cycle": 2, "current_phase": "ready"}), encoding="utf-8"
        )

        tool = _make_commit_tool(tmp_path)
        note_ctx = NoteContext()
        note_ctx.produce(ExclusionNote(file_path=_STATE_JSON))

        params = GitCommitInput(
            message="ready phase commit",
            workflow_phase="ready",
            base="main",
        )
        result = await tool.execute(params, note_ctx)

        assert not result.is_error, f"Expected commit success but got: {result}"
        assert not _has_net_diff(repo, _STATE_JSON, "main"), (
            f"D1 invariant violated (Scenario B): '{_STATE_JSON}' has net delta against 'main'"
        )
        # HEAD tree must contain the BASE version (v1), not the feature version (v2)
        head_content = repo.git.show(f"HEAD:{_STATE_JSON}")
        base_content = repo.git.show(f"main:{_STATE_JSON}")
        assert head_content == base_content, (
            f"Scenario B: HEAD tree '{_STATE_JSON}' must equal BASE version after neutralization. "
            f"HEAD: {head_content!r}, BASE: {base_content!r}"
        )
        assert _has_net_diff(repo, "normal.py", "main"), (
            "Sanity guard: 'normal.py' must have net delta against 'main'"
        )

    @pytest.mark.asyncio
    async def test_scenario_c_without_exclusion_notes_normal_commit_includes_all_files(
        self, tmp_path: Path
    ) -> None:
        """Scenario C: without ExclusionNotes, all changed files appear in the commit diff.

        Regression guard: the neutralize route must NOT fire on a normal commit.
        All modified files including .st3/state.json must appear in the net-diff
        when no ExclusionNotes are present.
        """
        repo = _init_repo_scenario_b(tmp_path)  # base has state.json — convenient setup

        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / _STATE_JSON).write_text(json.dumps({"cycle": 2}), encoding="utf-8")

        tool = _make_commit_tool(tmp_path)
        note_ctx = NoteContext()  # no ExclusionNotes

        params = GitCommitInput(
            message="normal commit, no exclusions",
            workflow_phase="documentation",
        )
        result = await tool.execute(params, note_ctx)

        assert not result.is_error, f"Expected commit success but got: {result}"
        # Both files must appear in the commit diff (no neutralization)
        assert _has_net_diff(repo, "normal.py", "main"), (
            "normal.py must be in diff after normal commit"
        )
        assert _has_net_diff(repo, _STATE_JSON, "main"), (
            f"'{_STATE_JSON}' must be in diff after normal commit (no ExclusionNotes)"
        )
