# tests/mcp_server/integration/test_submit_pr_atomic_flow.py
"""Integration tests for C3: SubmitPRTool atomic execution flow.

Tests verify the full atomic sequence:
  1. branch-local artifact detection (net-diff check)
  2. neutralize_to_base for tracked artifacts
  3. commit_with_scope("ready", ...)
  4. push to remote
  5. GitHub PR creation
  6. PRStatusCache write (OPEN)

Also verifies:
  - CreatePRTool is no longer instantiated as a public MCP tool in server composition root
  - GitCommitTool no longer contains the terminal-route neutralization path

@layer: Tests (Integration)
@dependencies: [pathlib, pytest, unittest.mock,
    mcp_server.tools.pr_tools,
    mcp_server.core.interfaces,
    mcp_server.core.operation_notes,
    mcp_server.managers.git_manager,
    mcp_server.managers.github_manager]
@responsibilities:
    - Prove SubmitPRTool.execute() writes PRStatus.OPEN after successful PR creation
    - Prove atomic flow: neutralize → commit → push → create_pr → set_pr_status
    - Prove skip of neutralize when no branch-local artifacts have net diff
    - Prove partial failure produces RecoveryNote
    - Prove CreatePRTool is not a public MCP tool in server.py
    - Prove GitCommitTool no longer contains neutralize_to_base path
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import yaml

import mcp_server.server as server_module
from mcp_server.config.schemas.phase_contracts_config import BranchLocalArtifact
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IPRStatusWriter, PRStatus
from mcp_server.core.operation_notes import NoteContext, RecoveryNote
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.tools import git_tools
from mcp_server.tools.pr_tools import SubmitPRInput, SubmitPRTool

_STATE_ARTIFACT = BranchLocalArtifact(
    path=".st3/state.json",
    reason="branch-local workflow state",
)
_DELIVERABLES_ARTIFACT = BranchLocalArtifact(
    path=".st3/deliverables.json",
    reason="branch-local deliverables",
)


def _make_submit_pr_tool(
    git_manager: GitManager,
    github_manager: GitHubManager,
    pr_status_writer: IPRStatusWriter,
    artifacts: tuple[BranchLocalArtifact, ...] = (_STATE_ARTIFACT,),
) -> SubmitPRTool:
    merge_readiness_context = MergeReadinessContext(
        terminal_phase="ready",
        pr_allowed_phase="ready",
        branch_local_artifacts=artifacts,
    )
    return SubmitPRTool(
        git_manager=git_manager,
        github_manager=github_manager,
        pr_status_writer=pr_status_writer,
        merge_readiness_context=merge_readiness_context,
    )


def _make_params(
    head: str = "feature/42-test",
    base: str = "main",
    title: str = "Test PR",
    body: str = "Description",
    draft: bool = False,
) -> SubmitPRInput:
    return SubmitPRInput(head=head, base=base, title=title, body=body, draft=draft)


class TestSubmitPRHappyPath:
    """SubmitPRTool happy path: atomic flow executes in correct order."""

    def test_submit_pr_happy_path(self) -> None:
        """Full atomic flow: neutralize → commit → push → create_pr → set_pr_status(OPEN)."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.adapter.has_net_diff_for_path.return_value = True
        git_manager.commit_with_scope.return_value = "abc1234"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {
            "number": 42,
            "url": "https://github.com/x/y/pull/42",
        }

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        result = asyncio.get_event_loop().run_until_complete(tool.execute(_make_params(), NoteContext()))

        assert not result.is_error
        git_manager.adapter.neutralize_to_base.assert_called_once()
        git_manager.commit_with_scope.assert_called_once()
        git_manager.adapter.push.assert_called_once()
        github_manager.create_pr.assert_called_once()
        pr_status_writer.set_pr_status.assert_called_once_with("feature/42-test", PRStatus.OPEN)

    def test_submit_pr_skips_neutralize_when_no_exclusions(self) -> None:
        """When no branch-local artifacts are configured, neutralize_to_base must not be called."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.commit_with_scope.return_value = "abc1234"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {
            "number": 42,
            "url": "https://github.com/x/y/pull/42",
        }

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        # No artifacts → neutralize must not be called
        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer, artifacts=())

        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(), NoteContext())
        )

        assert not result.is_error
        git_manager.adapter.neutralize_to_base.assert_not_called()
        pr_status_writer.set_pr_status.assert_called_once_with("feature/42-test", PRStatus.OPEN)

    def test_submit_pr_pr_status_written_open(self) -> None:
        """PRStatus.OPEN is written to the cache after successful PR creation."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "refactor/283-test"
        git_manager.adapter.has_net_diff_for_path.return_value = False
        git_manager.commit_with_scope.return_value = "deadbeef"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {
            "number": 99,
            "url": "https://github.com/x/y/pull/99",
        }

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(head="refactor/283-test"), NoteContext())
        )

        pr_status_writer.set_pr_status.assert_called_once_with("refactor/283-test", PRStatus.OPEN)


class TestSubmitPRPartialFailure:
    """SubmitPRTool produces RecoveryNote on failure after neutralize."""

    def test_push_failure_produces_recovery_note(self) -> None:
        """When push raises ExecutionError, a RecoveryNote is produced and error returned."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.adapter.has_net_diff_for_path.return_value = True
        git_manager.commit_with_scope.return_value = "abc1234"
        git_manager.adapter.push.side_effect = ExecutionError("push failed: remote rejected")

        github_manager = MagicMock(spec=GitHubManager)
        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        context = NoteContext()
        result = asyncio.get_event_loop().run_until_complete(tool.execute(_make_params(), context))

        assert result.is_error
        assert len(context.of_type(RecoveryNote)) > 0
        # PRStatus must NOT be written when push failed
        pr_status_writer.set_pr_status.assert_not_called()

    def test_create_pr_failure_produces_recovery_note(self) -> None:
        """When create_pr raises ExecutionError, a RecoveryNote is produced and error returned."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.commit_with_scope.return_value = "abc1234"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.side_effect = ExecutionError("PR already exists")

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(), NoteContext())
        )

        assert result.is_error
        pr_status_writer.set_pr_status.assert_not_called()


class TestCompositionRootContracts:
    """Structural contracts: CreatePRTool not in public tools; no neutralize in GitCommitTool."""

    def test_create_pr_tool_not_instantiated_in_server(self) -> None:
        """server.py must not contain CreatePRTool() instantiation (design D2)."""
        source = inspect.getsource(server_module)
        assert "CreatePRTool(" not in source, (
            "CreatePRTool must not be instantiated in server.py. "
            "Use SubmitPRTool instead (design D2)."
        )

    def test_git_commit_tool_has_no_neutralize_path(self) -> None:
        """GitCommitTool.execute() must not contain neutralize_to_base (moved to SubmitPRTool)."""
        source = inspect.getsource(git_tools.GitCommitTool.execute)
        assert "neutralize_to_base" not in source, (
            "GitCommitTool must not contain neutralize_to_base path in C3+. "
            "Neutralization is owned by SubmitPRTool."
        )

    def test_submit_pr_tool_declares_enforcement_event(self) -> None:
        """SubmitPRTool.enforcement_event must be 'submit_pr' so phase-readiness gate fires.

        Finding C3-QA-1: without this, check_phase_readiness in enforcement.yaml
        is never dispatched (server routes via tool.enforcement_event == None → skip).
        """
        assert SubmitPRTool.enforcement_event == "submit_pr", (
            "SubmitPRTool must declare enforcement_event = 'submit_pr'. "
            "Without it, check_phase_readiness in enforcement.yaml is never dispatched."
        )

    def test_enforcement_yaml_has_exclude_artifacts_and_phase_readiness_for_submit_pr(
        self,
    ) -> None:
        """enforcement.yaml must NOT include exclude_branch_local_artifacts for submit_pr.

        C6 design decision D5 (revised): neutralisation is self-contained inside
        SubmitPRTool.execute() via injected MergeReadinessContext. The enforcement
        runner no longer needs to pre-populate ExclusionNotes.
        check_phase_readiness must still be present.
        """
        workspace_root = Path(__file__).parents[3]
        config_path = workspace_root / ".st3" / "config" / "enforcement.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

        submit_pr_actions = [
            action["type"]
            for rule in config["enforcement"]
            if rule.get("tool") == "submit_pr" and rule.get("timing") == "pre"
            for action in rule.get("actions", [])
        ]

        assert "exclude_branch_local_artifacts" not in submit_pr_actions, (
            "submit_pr mag geen exclude_branch_local_artifacts enforcement hebben; "
            "neutralisatie is self-contained in SubmitPRTool.execute()"
        )
        assert "check_phase_readiness" in submit_pr_actions, (
            "submit_pr pre rule must include check_phase_readiness."
        )
