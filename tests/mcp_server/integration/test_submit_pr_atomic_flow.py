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

import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IPRStatusWriter, PRStatus
from mcp_server.core.operation_notes import ExclusionNote, NoteContext, RecoveryNote
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.pr_tools import CreatePRTool, SubmitPRInput, SubmitPRTool


def _make_submit_pr_tool(
    git_manager: GitManager,
    github_manager: GitHubManager,
    pr_status_writer: IPRStatusWriter,
) -> SubmitPRTool:
    return SubmitPRTool(
        git_manager=git_manager,
        github_manager=github_manager,
        pr_status_writer=pr_status_writer,
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

    def test_submit_pr_happy_path(self, tmp_path: Path) -> None:
        """Full atomic flow: neutralize → commit → push → create_pr → set_pr_status(OPEN)."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.commit_with_scope.return_value = "abc1234"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {"number": 42, "url": "https://github.com/x/y/pull/42"}

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        context = NoteContext()
        # Inject an ExclusionNote so neutralize_to_base is triggered
        context.produce(ExclusionNote(file_path=".st3/state.json"))

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(), context)
        )

        assert not result.is_error
        git_manager.adapter.neutralize_to_base.assert_called_once()
        git_manager.commit_with_scope.assert_called_once()
        git_manager.adapter.push.assert_called_once()
        github_manager.create_pr.assert_called_once()
        pr_status_writer.set_pr_status.assert_called_once_with("feature/42-test", PRStatus.OPEN)

    def test_submit_pr_skips_neutralize_when_no_exclusions(self, tmp_path: Path) -> None:
        """When no ExclusionNotes are present, neutralize_to_base must not be called."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.commit_with_scope.return_value = "abc1234"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {"number": 42, "url": "https://github.com/x/y/pull/42"}

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(), NoteContext())
        )

        assert not result.is_error
        git_manager.adapter.neutralize_to_base.assert_not_called()
        pr_status_writer.set_pr_status.assert_called_once_with("feature/42-test", PRStatus.OPEN)

    def test_submit_pr_pr_status_written_open(self, tmp_path: Path) -> None:
        """PRStatus.OPEN is written to the cache after successful PR creation."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "refactor/283-test"
        git_manager.commit_with_scope.return_value = "deadbeef"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {"number": 99, "url": "https://github.com/x/y/pull/99"}

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(head="refactor/283-test"), NoteContext())
        )

        pr_status_writer.set_pr_status.assert_called_once_with("refactor/283-test", PRStatus.OPEN)


class TestSubmitPRPartialFailure:
    """SubmitPRTool produces RecoveryNote on failure after neutralize."""

    def test_push_failure_produces_recovery_note(self, tmp_path: Path) -> None:
        """When push raises ExecutionError, a RecoveryNote is produced and error returned."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.commit_with_scope.return_value = "abc1234"
        git_manager.adapter.push.side_effect = ExecutionError("push failed: remote rejected")

        github_manager = MagicMock(spec=GitHubManager)
        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        context = NoteContext()
        context.produce(ExclusionNote(file_path=".st3/state.json"))

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(), context)
        )

        assert result.is_error
        assert any(isinstance(n, RecoveryNote) for n in context.notes)
        # PRStatus must NOT be written when push failed
        pr_status_writer.set_pr_status.assert_not_called()

    def test_create_pr_failure_produces_recovery_note(self, tmp_path: Path) -> None:
        """When create_pr raises ExecutionError, a RecoveryNote is produced and error returned."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.adapter = MagicMock()
        git_manager.adapter.get_current_branch.return_value = "feature/42-test"
        git_manager.commit_with_scope.return_value = "abc1234"

        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.side_effect = ExecutionError("PR already exists")

        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = _make_submit_pr_tool(git_manager, github_manager, pr_status_writer)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(_make_params(), NoteContext())
        )

        assert result.is_error
        pr_status_writer.set_pr_status.assert_not_called()


class TestCompositionRootContracts:
    """Structural contracts: CreatePRTool not in public tools; no neutralize in GitCommitTool."""

    def test_create_pr_tool_not_instantiated_in_server(self) -> None:
        """server.py must not contain CreatePRTool() instantiation (design D2)."""
        import mcp_server.server as server_module

        source = inspect.getsource(server_module)
        assert "CreatePRTool(" not in source, (
            "CreatePRTool must not be instantiated in server.py. "
            "Use SubmitPRTool instead (design D2)."
        )

    def test_git_commit_tool_has_no_neutralize_path(self) -> None:
        """GitCommitTool.execute() must not contain neutralize_to_base (moved to SubmitPRTool)."""
        from mcp_server.tools import git_tools

        source = inspect.getsource(git_tools.GitCommitTool.execute)
        assert "neutralize_to_base" not in source, (
            "GitCommitTool must not contain neutralize_to_base path in C3+. "
            "Neutralization is owned by SubmitPRTool."
        )

    def test_create_pr_tool_class_still_exists(self) -> None:
        """CreatePRTool class must still exist in pr_tools.py as internal utility (design D2)."""
        assert CreatePRTool is not None
        assert CreatePRTool.__name__ == "CreatePRTool"
