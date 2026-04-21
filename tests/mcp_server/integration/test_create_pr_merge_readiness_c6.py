# tests/mcp_server/integration/test_create_pr_merge_readiness_c6.py
"""
Integration tests for C6: create_pr merge-readiness gate correctness.

Tests the _has_net_diff_for_path proxy vs the false-positive _git_is_tracked proxy.

Scenario A (RED): state.json inherited from main (never re-committed on feature branch)
  â€” clean branch must NOT be blocked.
  â€” With _git_is_tracked (current): BLOCKED (false positive) â†’ test FAILS in RED.
  â€” With _has_net_diff_for_path (C6 GREEN): NOT blocked â†’ test PASSES.

Scenario B (regression): feature branch directly committed state.json
  â€” contaminated branch MUST be blocked by both proxies.

Structural check: test_enforcement_runner_c3.py must have zero private-method calls.

@layer: Tests (Integration)
@dependencies: [json, pathlib, pytest, git (GitPython),
    mcp_server.config.schemas.enforcement_config,
    mcp_server.config.schemas.phase_contracts_config,
    mcp_server.core.exceptions,
    mcp_server.core.operation_notes,
    mcp_server.managers.enforcement_runner,
    mcp_server.managers.phase_contract_resolver]
@responsibilities:
    - Prove _has_net_diff_for_path does not produce false positives for inherited files
    - Prove contaminated branches are still blocked after C6 proxy replacement
    - Prove Principle-14 compliance: no private-method calls in test_enforcement_runner_c3.py
"""

# Standard library
import json
from pathlib import Path
from types import SimpleNamespace

# Third-party
import pytest
from git import Repo as GitRepo

from mcp_server.config.schemas.enforcement_config import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementRule,
)
from mcp_server.config.schemas.phase_contracts_config import BranchLocalArtifact
from mcp_server.core.exceptions import ValidationError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import EnforcementContext, EnforcementRunner
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext

_STATE_JSON = ".st3/state.json"

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

_ARTIFACT_STATE = BranchLocalArtifact(
    path=_STATE_JSON,
    reason="MCP workflow state â€” branch-local, must never reach main",
)

_CREATE_PR_CONFIG = EnforcementConfig(
    enforcement=[
        EnforcementRule(
            event_source="tool",
            tool="create_pr",
            timing="pre",
            actions=[EnforcementAction(type="check_merge_readiness")],
        )
    ]
)


def _init_repo_with_state_on_main(repo_dir: Path) -> GitRepo:
    """Init repo where main branch has state.json committed (historical scenario).

    This represents a repository where state.json was previously committed on main
    (e.g. from an earlier development session). A new feature branch created from
    this main will INHERIT state.json in its file tree.

    The false positive: _git_is_tracked returns True for state.json on the feature
    branch (it is in the tracked files list, inherited from main), even though the
    feature branch never introduced any net delta for that file.
    """
    repo = GitRepo.init(str(repo_dir))
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    state_dir = repo_dir / ".st3"
    state_dir.mkdir(parents=True)
    (repo_dir / "app.py").write_text("# app v1\n", encoding="utf-8")
    (state_dir / "state.json").write_text(
        json.dumps({"current_phase": "implementation", "branch": "main"}),
        encoding="utf-8",
    )
    repo.index.add(["app.py", _STATE_JSON])
    repo.index.commit("initial: add app.py and state.json on main")
    # Ensure the default branch is named 'main' regardless of git config
    if repo.active_branch.name != "main":
        repo.head.reference.rename("main")
    return repo


def _make_runner(tmp_path: Path) -> EnforcementRunner:
    merge_ctx = MergeReadinessContext(
        terminal_phase="ready",
        pr_allowed_phase="ready",
        branch_local_artifacts=(_ARTIFACT_STATE,),
    )
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=_CREATE_PR_CONFIG,
        merge_readiness_context=merge_ctx,
    )


def _write_ready_state(tmp_path: Path, branch: str) -> None:
    state_path = tmp_path / ".st3" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"current_phase": "ready", "branch": branch}),
        encoding="utf-8",
    )


class TestCreatePRMergeReadinessC6:
    """C6: _has_net_diff_for_path proxy semantics for create_pr merge-readiness gate."""

    def test_create_pr_not_blocked_on_clean_branch(self, tmp_path: Path) -> None:
        """Clean branch (state.json inherited from main, never re-committed) must NOT be blocked.

        C6 RED: Fails with _git_is_tracked (git ls-files returns 0 because state.json IS
        in the tracked file tree, inherited from the main branch commit). The correct proxy
        is _has_net_diff_for_path (net delta on this branch = zero â†’ not blocked).

        Planning.md Â§3.9: _git_is_tracked tests HEAD tree not net delta â€” false positive.
        """
        # Setup: main has state.json committed; feature branch never touches it.
        repo = _init_repo_with_state_on_main(tmp_path)

        # Create and checkout feature branch from main
        feature_branch = repo.create_head("feature/clean-branch")
        feature_branch.checkout()

        # Add a real commit on this branch (but NOT touching state.json)
        (tmp_path / "work.py").write_text("# feature work\n", encoding="utf-8")
        repo.index.add(["work.py"])
        repo.index.commit("feat: add work.py")

        # Write ready phase to state.json on disk (not committed â€” just the file system)
        _write_ready_state(tmp_path, "feature/clean-branch")

        runner = _make_runner(tmp_path)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(base="main"),
        )

        # Should NOT raise â€” clean branch must not be blocked.
        # RED: Currently raises ValidationError because _git_is_tracked returns True
        #      for state.json (it is in the tracked file tree from main's commit).
        runner.run(
            event="create_pr",
            timing="pre",
            enforcement_ctx=ctx,
            note_context=NoteContext(),
        )

    def test_create_pr_blocked_on_contaminated_branch(self, tmp_path: Path) -> None:
        """Branch that directly committed state.json MUST be blocked (regression guard).

        Both _git_is_tracked and _has_net_diff_for_path should block this scenario.
        """
        # Setup: main without state.json; feature branch commits it directly (bad workflow).
        repo = GitRepo.init(str(tmp_path))
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Test")
            cw.set_value("user", "email", "test@example.com")

        (tmp_path / "app.py").write_text("# app\n", encoding="utf-8")
        repo.index.add(["app.py"])
        repo.index.commit("initial: add app.py (no state.json on main)")
        # Ensure the default branch is named 'main' regardless of git config
        if repo.active_branch.name != "main":
            repo.head.reference.rename("main")

        feature_branch = repo.create_head("feature/contaminated")
        feature_branch.checkout()

        # Contaminate: commit state.json on this feature branch (bad workflow)
        state_dir = tmp_path / ".st3"
        state_dir.mkdir(parents=True)
        (state_dir / "state.json").write_text(
            json.dumps({"current_phase": "implementation", "branch": "feature/contaminated"}),
            encoding="utf-8",
        )
        repo.index.add([_STATE_JSON])
        repo.index.commit("bad: accidentally committed state.json on feature branch")

        # Write ready phase to state.json (simulating ready-phase transition)
        _write_ready_state(tmp_path, "feature/contaminated")

        runner = _make_runner(tmp_path)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(base="main"),
        )

        with pytest.raises(ValidationError, match="net delta"):
            runner.run(
                event="create_pr",
                timing="pre",
                enforcement_ctx=ctx,
                note_context=NoteContext(),
            )


def test_enforcement_runner_c3_has_no_private_method_calls() -> None:
    """Principle 14: test_enforcement_runner_c3.py must not directly call private methods.

    C6 RED: Fails because test_enforcement_runner_c3.py currently calls
    _handle_exclude_branch_local_artifacts and accesses _merge_readiness_context directly.
    After C6 GREEN (rewriting to use public run() API), this test passes.

    Planning.md Â§3.14: Private method call patterns in test_enforcement_runner_c3.py
    are exactly the pattern ARCHITECTURE_PRINCIPLES Â§14 forbids.
    """
    test_file = Path(__file__).parent.parent / "unit" / "managers" / "test_enforcement_runner_c3.py"
    source = test_file.read_text(encoding="utf-8")

    assert "_handle_exclude_branch_local_artifacts" not in source, (
        "Principle 14 violation: test_enforcement_runner_c3.py calls private method "
        "_handle_exclude_branch_local_artifacts directly. Replace with runner.run() API."
    )
    assert "_handle_check_merge_readiness" not in source, (
        "Principle 14 violation: test_enforcement_runner_c3.py calls private method "
        "_handle_check_merge_readiness directly. Replace with runner.run() API."
    )
    assert "_merge_readiness_context" not in source, (
        "Principle 14 violation: test_enforcement_runner_c3.py accesses private attribute "
        "_merge_readiness_context directly. Replace with behavioral assertion via run() API."
    )
