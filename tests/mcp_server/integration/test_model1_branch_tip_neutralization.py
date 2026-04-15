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


def _init_repo(repo_dir: Path) -> GitRepo:
    """Create a real git repo with a base commit tracking excluded + normal files.

    Branch layout after setup:
        main (initial commit M) ← feature/test (current HEAD, no extra commits yet)

    Files committed on main (and inherited by feature):
        normal.py          → "# v1\\n"
        .st3/state.json    → {"cycle": 1}
        .st3/deliverables.json → {}
    """
    repo = GitRepo.init(str(repo_dir))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    repo.git.checkout("-b", "main")

    normal = repo_dir / "normal.py"
    state_dir = repo_dir / ".st3"
    state_dir.mkdir(parents=True, exist_ok=True)

    normal.write_text("# v1\n", encoding="utf-8")
    (state_dir / "state.json").write_text('{"cycle": 1}', encoding="utf-8")
    (state_dir / "deliverables.json").write_text("{}", encoding="utf-8")

    repo.index.add(["normal.py", _STATE_JSON, _DELIVERABLES_JSON])
    repo.index.commit("initial commit")

    # Fork a feature branch from this base commit
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
    async def test_excluded_path_has_zero_net_diff_after_commit(self, tmp_path: Path) -> None:
        """D1 invariant: excluded path absent from git diff merge_base..HEAD after commit.

        Setup:
            - feature/test branched from main (initial commit = merge base)
            - state.json modified on feature branch
            - normal.py modified on feature branch
        Proof:
            - GitCommitTool with ExclusionNote for state.json
            - After commit: git diff merge_base..HEAD -- .st3/state.json is empty
            - After commit: normal.py IS in git diff merge_base..HEAD (sanity guard)
        """
        repo = _init_repo(tmp_path)

        # Simulate work: modify both the excluded path and a normal file
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
            f"D1 invariant violated: '{_STATE_JSON}' still has net delta against 'main'"
        )
        assert _has_net_diff(repo, "normal.py", "main"), (
            "Sanity guard failed: 'normal.py' should have net delta against 'main'"
        )

    @pytest.mark.asyncio
    async def test_multiple_excluded_paths_all_zero_net_diff(self, tmp_path: Path) -> None:
        """D1 invariant holds for multiple excluded paths simultaneously.

        Both state.json and deliverables.json are excluded via ExclusionNote.
        Neither must appear in git diff merge_base..HEAD after the commit.
        """
        repo = _init_repo(tmp_path)

        (tmp_path / "normal.py").write_text("# v2\n", encoding="utf-8")
        (tmp_path / _STATE_JSON).write_text(
            json.dumps({"cycle": 2, "current_phase": "ready"}), encoding="utf-8"
        )
        (tmp_path / _DELIVERABLES_JSON).write_text(
            json.dumps({"deliverable": "test"}), encoding="utf-8"
        )

        tool = _make_commit_tool(tmp_path)
        note_ctx = NoteContext()
        note_ctx.produce(ExclusionNote(file_path=_STATE_JSON))
        note_ctx.produce(ExclusionNote(file_path=_DELIVERABLES_JSON))

        params = GitCommitInput(
            message="ready phase commit",
            workflow_phase="ready",
            base="main",
        )
        result = await tool.execute(params, note_ctx)

        assert not result.is_error, f"Expected commit success but got: {result}"
        assert not _has_net_diff(repo, _STATE_JSON, "main"), (
            f"D1 invariant violated: '{_STATE_JSON}' still has net delta against 'main'"
        )
        assert not _has_net_diff(repo, _DELIVERABLES_JSON, "main"), (
            f"D1 invariant violated: '{_DELIVERABLES_JSON}' still has net delta against 'main'"
        )
        assert _has_net_diff(repo, "normal.py", "main"), (
            "Sanity guard failed: 'normal.py' should have net delta against 'main'"
        )

    @pytest.mark.asyncio
    async def test_without_exclusion_notes_normal_commit_includes_all_files(
        self, tmp_path: Path
    ) -> None:
        """Without ExclusionNotes, all changed files appear in the commit diff.

        Regression guard: the neutralize route must NOT fire on a normal commit.
        Normal files including state.json must appear in git diff when no
        ExclusionNotes are present.
        """
        repo = _init_repo(tmp_path)

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
