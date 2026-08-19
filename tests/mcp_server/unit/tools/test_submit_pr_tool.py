# tests/mcp_server/unit/tools/test_submit_pr_tool.py
"""Unit tests for SubmitPRTool and SubmitPRInput scaffold.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.pr_tools]
"""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.interfaces import IBranchParentReader, IPRStatusWriter
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.schemas.github_models import PRReadModel
from mcp_server.schemas.tool_outputs import PROutput
from mcp_server.tools.pr_tools import SubmitPRInput, SubmitPRTool
from tests.mcp_server.test_support import get_default_server_root


class TestSubmitPRInput:
    """SubmitPRInput Pydantic model has the required fields per design 3.2."""

    def test_head_field_required(self) -> None:
        assert "head" in SubmitPRInput.model_fields

    def test_title_field_required(self) -> None:
        assert "title" in SubmitPRInput.model_fields

    def test_base_field_optional(self) -> None:
        field = SubmitPRInput.model_fields.get("base")
        assert field is not None
        assert not field.is_required()

    def test_draft_field_optional(self) -> None:
        field = SubmitPRInput.model_fields.get("draft")
        assert field is not None
        assert not field.is_required()


class TestSubmitPRTool:
    """SubmitPRTool is a BranchMutatingTool named 'submit_pr'."""

    def test_class_exists(self) -> None:
        assert SubmitPRTool is not None

    def test_is_branch_mutating_in_config(self) -> None:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        loader = ConfigLoader(config_root=repo_root / get_default_server_root() / "config")
        config_path = repo_root / get_default_server_root() / "config" / "enforcement.yaml"
        config = loader.load_enforcement_config(config_path=config_path)
        assert "submit_pr" in config.categories.get("branch_mutating", [])

    def test_name_is_submit_pr(self) -> None:
        tool = SubmitPRTool(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
        assert tool.name == "submit_pr"

    def test_args_model_is_submit_pr_input(self) -> None:
        tool = SubmitPRTool(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
        assert tool.args_model is SubmitPRInput


def _make_tool_for_lod(
    git_manager: GitManager,
    github_manager: GitHubManager,
    pr_status_writer: IPRStatusWriter,
) -> SubmitPRTool:
    mock_pr = PRReadModel(
        pr_number=1,
        title="Test PR",
        state="open",
        base_branch="main",
        head_branch="feature/42-test",
        merged_at=None,
        merge_sha=None,
        body="",
        html_url="https://github.com/x/y/pull/1",
    )
    github_manager.get_pr.return_value = mock_pr
    merge_readiness_context = MergeReadinessContext(
        terminal_phase="ready",
        pr_allowed_phase="ready",
        branch_local_artifacts=[],
    )
    return SubmitPRTool(
        git_manager=git_manager,
        github_manager=github_manager,
        pr_status_writer=pr_status_writer,
        merge_readiness_context=merge_readiness_context,
        branch_parent_reader=MagicMock(spec=IBranchParentReader),
    )


class TestSubmitPRToolLoD:
    """C5 LoD structural tests: execute() must not call git internals directly."""

    def test_submit_pr_execute_does_not_call_git_internals_directly(
        self,
    ) -> None:
        """execute() must only call GitManager.prepare_submission, not lower-level methods."""
        git_manager = MagicMock(spec=GitManager)
        git_manager.get_current_branch.return_value = "feature/42-test"
        git_manager.prepare_submission.return_value = False
        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {
            "number": 1,
            "url": "https://github.com/x/y/pull/1",
        }
        pr_status_writer = MagicMock(spec=IPRStatusWriter)
        tool = _make_tool_for_lod(git_manager, github_manager, pr_status_writer)
        params = SubmitPRInput(head="feature/42-test", base="main", title="Test PR")

        asyncio.run(tool.execute(params, NoteContext()))

        # These methods must NOT be called directly by execute() (LoD violation)
        git_manager.neutralize_to_base.assert_not_called()
        git_manager.commit_with_scope.assert_not_called()
        git_manager.push.assert_not_called()
        git_manager.has_net_diff_for_path.assert_not_called()

    def test_submit_pr_execute_does_not_access_adapter(
        self,
    ) -> None:
        """execute() must not call self._git_manager.adapter directly."""
        source = inspect.getsource(SubmitPRTool.execute)
        assert "_git_manager.adapter" not in source, (
            "SubmitPRTool.execute() must not access GitAdapter directly. "
            "Use GitManager methods instead (Law of Demeter)."
        )


def _make_tool_with_reader(
    git_manager: GitManager,
    github_manager: GitHubManager,
    pr_status_writer: IPRStatusWriter,
    branch_parent_reader: IBranchParentReader,
) -> SubmitPRTool:
    """Build SubmitPRTool with branch_parent_reader for C4 base-resolution tests."""
    mock_pr = PRReadModel(
        pr_number=1,
        title="Test PR",
        state="open",
        base_branch="main",
        head_branch="feature/42-test",
        merged_at=None,
        merge_sha=None,
        body="",
        html_url="https://github.com/x/y/pull/1",
    )
    github_manager.get_pr.return_value = mock_pr
    merge_readiness_context = MergeReadinessContext(
        terminal_phase="ready",
        pr_allowed_phase="ready",
        branch_local_artifacts=[],
    )
    return SubmitPRTool(
        git_manager=git_manager,
        github_manager=github_manager,
        pr_status_writer=pr_status_writer,
        merge_readiness_context=merge_readiness_context,
        branch_parent_reader=branch_parent_reader,
    )


class TestSubmitPRToolBaseResolution:
    """C4: SubmitPRTool.execute() resolves base via params.base → reader → default."""

    def _make_git_manager(self, default_base: str = "main") -> MagicMock:
        git_manager = MagicMock(spec=GitManager)
        git_manager.get_current_branch.return_value = "feature/42-test"
        git_manager.prepare_submission.return_value = False
        git_manager.git_config = MagicMock()
        git_manager.git_config.default_base_branch = default_base
        return git_manager

    def _make_github_manager(self) -> MagicMock:
        github_manager = MagicMock(spec=GitHubManager)
        github_manager.create_pr.return_value = {
            "number": 1,
            "url": "https://github.com/x/y/pull/1",
        }
        return github_manager

    def test_params_base_wins_over_reader(self) -> None:
        """C4.D3: params.base takes priority; reader.get_parent_branch is not called."""
        git_manager = self._make_git_manager()
        github_manager = self._make_github_manager()
        reader = MagicMock(spec=IBranchParentReader)
        pr_status_writer = MagicMock(spec=IPRStatusWriter)
        tool = _make_tool_with_reader(git_manager, github_manager, pr_status_writer, reader)
        params = SubmitPRInput(head="feature/42-test", base="my-explicit-base", title="Test PR")

        asyncio.run(tool.execute(params, NoteContext()))

        reader.get_parent_branch.assert_not_called()
        _, kwargs = github_manager.create_pr.call_args
        assert kwargs["base"] == "my-explicit-base"

    def test_reader_used_when_params_base_none(self) -> None:
        """C4.D3: reader.get_parent_branch result used when params.base is None."""
        git_manager = self._make_git_manager()
        github_manager = self._make_github_manager()
        reader = MagicMock(spec=IBranchParentReader)
        reader.get_parent_branch.return_value = "epic/320-production-readiness"
        pr_status_writer = MagicMock(spec=IPRStatusWriter)
        tool = _make_tool_with_reader(git_manager, github_manager, pr_status_writer, reader)
        params = SubmitPRInput(head="feature/42-test", title="Test PR")

        asyncio.run(tool.execute(params, NoteContext()))

        reader.get_parent_branch.assert_called_once_with("feature/42-test")
        _, kwargs = github_manager.create_pr.call_args
        assert kwargs["base"] == "epic/320-production-readiness"

    def test_fallback_to_default_when_reader_returns_none(self) -> None:
        """C4.D3: default_base_branch used when params.base and reader both return None."""
        git_manager = self._make_git_manager(default_base="main")
        github_manager = self._make_github_manager()
        reader = MagicMock(spec=IBranchParentReader)
        reader.get_parent_branch.return_value = None
        pr_status_writer = MagicMock(spec=IPRStatusWriter)
        tool = _make_tool_with_reader(git_manager, github_manager, pr_status_writer, reader)
        params = SubmitPRInput(head="feature/42-test", title="Test PR")

        asyncio.run(tool.execute(params, NoteContext()))

        reader.get_parent_branch.assert_called_once_with("feature/42-test")
        _, kwargs = github_manager.create_pr.call_args
        assert kwargs["base"] == "main"


class TestSubmitPRToolExecute:
    """Tests verify that SubmitPRTool execution returns the new DTO."""

    @pytest.mark.asyncio
    async def test_submit_pr_returns_dto(self) -> None:
        git_manager = MagicMock(spec=GitManager)
        git_manager.get_current_branch.return_value = "feature/42-test"
        git_manager.prepare_submission.return_value = False
        github_manager = MagicMock(spec=GitHubManager)

        mock_pr = PRReadModel(
            pr_number=1,
            title="Test PR",
            state="open",
            base_branch="main",
            head_branch="feature/42-test",
            merged_at=None,
            merge_sha=None,
            body="",
            html_url="https://github.com/x/y/pull/1",
        )
        github_manager.create_pr.return_value = {
            "number": 1,
            "url": "https://github.com/x/y/pull/1",
        }
        github_manager.get_pr.return_value = mock_pr

        pr_status_writer = MagicMock(spec=IPRStatusWriter)
        tool = _make_tool_for_lod(git_manager, github_manager, pr_status_writer)
        params = SubmitPRInput(head="feature/42-test", base="main", title="Test PR")

        result = await tool.execute(params, NoteContext())
        assert isinstance(result, PROutput)
        assert result.success is True
        assert result.number == 1
        assert result.title == "Test PR"
        assert result.html_url == "https://github.com/x/y/pull/1"
