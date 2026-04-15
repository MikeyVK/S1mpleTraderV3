# tests/mcp_server/integration/test_create_pr_merge_readiness_c6.py
"""
Integration tests for C6: create_pr merge-readiness gate correctness.

Tests the _has_net_diff_for_path proxy vs the false-positive _git_is_tracked proxy.

Scenario A (RED): state.json inherited from main (never re-committed on feature branch)
  — clean branch must NOT be blocked.
  — With _git_is_tracked (current): BLOCKED (false positive) → test FAILS in RED.
  — With _has_net_diff_for_path (C6 GREEN): NOT blocked → test PASSES.

Scenario B (regression): feature branch directly committed state.json
  — contaminated branch MUST be blocked by both proxies.

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
from shutil import copytree
from types import SimpleNamespace
from unittest.mock import patch

# Third-party
import pytest
from git import Repo as GitRepo
from mcp.types import CallToolRequest, CallToolRequestParams

# Project modules
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
from mcp_server.server import MCPServer

_STATE_JSON = ".st3/state.json"

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

_ARTIFACT_STATE = BranchLocalArtifact(
    path=_STATE_JSON,
    reason="MCP workflow state — branch-local, must never reach main",
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
        is _has_net_diff_for_path (net delta on this branch = zero → not blocked).

        Planning.md §3.9: _git_is_tracked tests HEAD tree not net delta — false positive.
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

        # Write ready phase to state.json on disk (not committed — just the file system)
        _write_ready_state(tmp_path, "feature/clean-branch")

        runner = _make_runner(tmp_path)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(base="main"),
        )

        # Should NOT raise — clean branch must not be blocked.
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

    Planning.md §3.14: Private method call patterns in test_enforcement_runner_c3.py
    are exactly the pattern ARCHITECTURE_PRINCIPLES §14 forbids.
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


class TestCreatePRMergeReadinessC6ServerDispatch:
    """C6 server-dispatch: create_pr merge-readiness gate via MCPServer.handle_call_tool.

    Proves that the _has_net_diff_for_path proxy is correctly wired through the full
    MCPServer dispatch path — not just at the EnforcementRunner layer.
    """

    @pytest.mark.asyncio
    async def test_server_dispatch_clean_branch_create_pr_not_blocked(self, tmp_path: Path) -> None:
        """MCPServer dispatch: create_pr on clean branch (state.json inherited) must succeed.

        Scenario: main has state.json committed; feature branch never touches it.
        _has_net_diff_for_path returns False → merge-readiness gate must pass →
        GitHub create_pr must be called (mocked to avoid network).

        This proves the full wire-through: MCPServer pre-enforcement hook →
        EnforcementRunner._handle_check_merge_readiness →
        _has_net_diff_for_path → no ValidationError raised.
        """
        # Init repo: main has state.json, feature branch never modifies it
        repo = _init_repo_with_state_on_main(tmp_path)
        feature_branch = repo.create_head("feature/clean-branch")
        feature_branch.checkout()
        (tmp_path / "work.py").write_text("# feature work\n", encoding="utf-8")
        repo.index.add(["work.py"])
        repo.index.commit("feat: add work.py")

        # Copy configs and write ready-phase state
        config_dir = tmp_path / ".st3" / "config"
        copytree(_REPO_ROOT / ".st3" / "config", config_dir, dirs_exist_ok=True)
        _write_ready_state(tmp_path, "feature/clean-branch")

        with patch("mcp_server.server.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(config_dir)
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.github.token = "test-token"
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"
            server = MCPServer()

        # Mock GitHub create_pr to avoid real network call
        mock_pr_result = {"number": 42, "url": "https://github.com/test/repo/pull/42"}
        with patch.object(
            server.github_manager,
            "create_pr",
            return_value=mock_pr_result,
        ) as mock_create_pr:
            handler = server.server.request_handlers[CallToolRequest]
            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="create_pr",
                    arguments={
                        "title": "C6 clean branch PR",
                        "body": "Merge-readiness gate must not block clean branch",
                        "head": "feature/clean-branch",
                        "base": "main",
                    },
                )
            )
            response = await handler(req)

        content_texts = [c.text for c in response.root.content if hasattr(c, "text")]
        all_text = " ".join(content_texts)

        # Gate must NOT block — create_pr must have been called
        assert not response.root.isError, (
            f"Clean branch was blocked by merge-readiness gate (false positive). "
            f"Response: {all_text!r}"
        )
        mock_create_pr.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_dispatch_contaminated_branch_create_pr_blocked(
        self, tmp_path: Path
    ) -> None:
        """MCPServer dispatch: create_pr on contaminated branch must be blocked with error.

        Scenario: feature branch directly committed state.json.
        _has_net_diff_for_path returns True → ValidationError raised → MCPServer
        returns isError=True response — GitHub create_pr must NOT be called.
        """
        # Init repo: main has NO state.json; feature branch commits it directly
        repo = GitRepo.init(str(tmp_path))
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Test")
            cw.set_value("user", "email", "test@example.com")
        (tmp_path / "app.py").write_text("# app\n", encoding="utf-8")
        repo.index.add(["app.py"])
        repo.index.commit("initial: add app.py (no state.json on main)")
        if repo.active_branch.name != "main":
            repo.head.reference.rename("main")

        feature_branch = repo.create_head("feature/contaminated")
        feature_branch.checkout()
        state_dir = tmp_path / ".st3"
        state_dir.mkdir(parents=True)
        (state_dir / "state.json").write_text(
            json.dumps({"current_phase": "implementation", "branch": "feature/contaminated"}),
            encoding="utf-8",
        )
        repo.index.add([_STATE_JSON])
        repo.index.commit("bad: accidentally committed state.json on feature branch")

        config_dir = tmp_path / ".st3" / "config"
        copytree(_REPO_ROOT / ".st3" / "config", config_dir, dirs_exist_ok=True)
        _write_ready_state(tmp_path, "feature/contaminated")

        with patch("mcp_server.server.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(config_dir)
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.github.token = "test-token"
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"
            server = MCPServer()

        with patch.object(
            server.github_manager,
            "create_pr",
            side_effect=AssertionError("create_pr must not be called on contaminated branch"),
        ) as mock_create_pr:
            handler = server.server.request_handlers[CallToolRequest]
            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="create_pr",
                    arguments={
                        "title": "C6 contaminated branch PR",
                        "body": "This should be blocked",
                        "head": "feature/contaminated",
                        "base": "main",
                    },
                )
            )
            response = await handler(req)

        content_texts = [c.text for c in response.root.content if hasattr(c, "text")]
        all_text = " ".join(content_texts)

        assert response.root.isError is True, (
            f"Contaminated branch was NOT blocked — enforcement gate failed. Response: {all_text!r}"
        )
        assert "net delta" in all_text, f"Expected 'net delta' in error response. Got: {all_text!r}"
        mock_create_pr.assert_not_called()
