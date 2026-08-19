"""Integration tests for all MCP server tools.

Phase 1.3: Verify all tools are operational and return expected results.
These tests use mocks but test the full flow from Tool -> Manager -> Adapter.

@layer: Tests (Integration)
@dependencies: pytest, unittest.mock, mcp_server.tools
"""

from unittest.mock import ANY, MagicMock

import pytest

from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import GitPushResult
from mcp_server.managers.pytest_runner import PytestRunner
from mcp_server.schemas.github_models import IssueReadModel

# Git Tools
from mcp_server.tools.git_tools import (
    CreateBranchInput,
    CreateBranchTool,
    GitCheckoutInput,
    GitCheckoutTool,
    GitCommitInput,
    GitCommitTool,
    GitDeleteBranchInput,
    GitDeleteBranchTool,
    GitMergeInput,
    GitMergeTool,
    GitPushInput,
    GitPushTool,
    GitRestoreInput,
    GitRestoreTool,
    GitStashInput,
    GitStashTool,
    GitStatusInput,
    GitStatusTool,
)

# Development Tools
from mcp_server.tools.health_tools import HealthCheckInput, HealthCheckTool

# GitHub Tools (imported here for availability, require manager injection)
from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool
from mcp_server.tools.label_tools import AddLabelsInput, AddLabelsTool

# Quality Tools
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool
from mcp_server.tools.scaffold_schema_tool import ScaffoldSchemaTool
from mcp_server.tools.test_tools import RunTestsTool


def make_mock_git_config() -> MagicMock:
    git_config = MagicMock()
    git_config.default_base_branch = "main"
    git_config.issue_title_max_length = 72
    git_config.branch_types = ["feature", "bug", "docs", "refactor", "hotfix", "epic"]
    git_config.commit_types = ["feat", "fix", "docs", "refactor", "test", "chore"]
    git_config.has_branch_type.return_value = True
    git_config.has_commit_type.return_value = True
    git_config.extract_issue_number.return_value = None
    return git_config


def make_mock_git_manager() -> MagicMock:
    manager = MagicMock()
    manager.git_config = make_mock_git_config()
    manager.adapter = MagicMock()
    manager.adapter.get_current_branch.return_value = "feature/test"
    manager.get_status.return_value = {
        "branch": "main",
        "is_clean": True,
        "untracked_files": [],
        "modified_files": [],
    }
    manager.stash_list.return_value = []
    manager.push.return_value = GitPushResult(
        branch="feature/test",
        set_upstream=False,
        new_upstream_created=False,
    )
    return manager


def make_mock_label_config() -> MagicMock:
    label_config = MagicMock()
    medium_priority = MagicMock()
    medium_priority.name = "priority:medium"
    label_config.get_labels_by_category.return_value = [medium_priority]
    label_config.label_exists.return_value = True
    return label_config


def make_mock_qa_manager() -> MagicMock:
    manager = MagicMock()
    manager.resolve_scope.return_value = ["test.py"]
    manager.run_quality_gates.return_value = {
        "overall_pass": True,
        "summary": {
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "total_violations": 0,
            "auto_fixable": 0,
        },
        "gates": [
            {
                "name": "Linting",
                "passed": True,
                "status": "passed",
                "score": "10/10",
                "issues": [],
            }
        ],
    }
    manager.build_compact_result.return_value = {
        "overall_pass": True,
        "duration_ms": 0,
        "gates": [
            {
                "id": "Linting",
                "passed": True,
                "skipped": False,
                "status": "passed",
                "violations": [],
            }
        ],
    }
    return manager


def make_create_branch_tool(manager: MagicMock | None = None) -> CreateBranchTool:
    return CreateBranchTool(manager=manager or make_mock_git_manager())


def make_git_status_tool(manager: MagicMock | None = None) -> GitStatusTool:
    return GitStatusTool(manager=manager or make_mock_git_manager())


def make_git_commit_tool(manager: MagicMock | None = None) -> GitCommitTool:
    return GitCommitTool(manager=manager or make_mock_git_manager())


def make_git_restore_tool(manager: MagicMock | None = None) -> GitRestoreTool:
    return GitRestoreTool(manager=manager or make_mock_git_manager())


def make_git_checkout_tool(manager: MagicMock | None = None) -> GitCheckoutTool:
    return GitCheckoutTool(manager=manager or make_mock_git_manager())


def make_git_push_tool(manager: MagicMock | None = None) -> GitPushTool:
    return GitPushTool(manager=manager or make_mock_git_manager())


def make_git_merge_tool(manager: MagicMock | None = None) -> GitMergeTool:
    return GitMergeTool(manager=manager or make_mock_git_manager())


def make_git_delete_branch_tool(manager: MagicMock | None = None) -> GitDeleteBranchTool:
    return GitDeleteBranchTool(manager=manager or make_mock_git_manager())


def make_git_stash_tool(manager: MagicMock | None = None) -> GitStashTool:
    return GitStashTool(manager=manager or make_mock_git_manager())


def make_run_quality_gates_tool(manager: MagicMock | None = None) -> RunQualityGatesTool:
    return RunQualityGatesTool(manager=manager or make_mock_qa_manager())


def make_create_issue_tool(manager: MagicMock) -> CreateIssueTool:
    issue_config = MagicMock()
    issue_config.has_issue_type.return_value = True
    issue_config.get_workflow.return_value = "feature"
    issue_config.get_label.side_effect = lambda issue_type: f"type:{issue_type}"

    scope_config = MagicMock()
    scope_config.has_scope.return_value = True

    milestone_config = MagicMock()
    milestone_config.validate_milestone.return_value = True
    milestone_config.milestones = []

    contributor_config = MagicMock()
    contributor_config.validate_assignee.return_value = True

    contracts_config = MagicMock()
    contracts_config.get_first_phase.return_value = "research"

    return CreateIssueTool(
        manager=manager,
        issue_config=issue_config,
        milestone_config=milestone_config,
        contracts_config=contracts_config,
        label_config=MagicMock(),
        scope_config=scope_config,
        git_config=MagicMock(),
    )


def make_add_labels_tool(manager: MagicMock) -> AddLabelsTool:
    return AddLabelsTool(
        manager=manager,
        label_config=make_mock_label_config(),
        workphases_config=MagicMock(),
    )


def make_core_tools() -> list[object]:
    return [
        make_create_branch_tool(),
        make_git_checkout_tool(),
        make_git_stash_tool(),
        make_git_status_tool(),
        make_git_restore_tool(),
        make_git_commit_tool(),
        make_git_merge_tool(),
        make_git_push_tool(),
        make_git_delete_branch_tool(),
        make_run_quality_gates_tool(),
        HealthCheckTool(),
        RunTestsTool(runner=PytestRunner()),
        ScaffoldSchemaTool(manager=MagicMock()),
    ]


class TestGitToolsIntegration:
    """Integration tests for all Git tools."""

    @pytest.mark.asyncio
    async def test_create_branch_tool_flow(self) -> None:
        """Test create branch tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.create_branch.return_value = "feature/test-feature"

        tool = make_create_branch_tool(mock_manager)
        result = await tool.execute(
            CreateBranchInput(name="test-feature", branch_type="feature", base_branch="HEAD"),
            NoteContext(),
        )

        assert result.branch_name == "feature/test-feature"
        mock_manager.create_branch.assert_called_once_with("test-feature", "feature", "HEAD", ANY)

    @pytest.mark.asyncio
    async def test_git_status_tool_flow(self) -> None:
        """Test git status tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.get_status.return_value = {
            "branch": "main",
            "is_clean": True,
            "untracked_files": [],
            "modified_files": [],
        }

        tool = make_git_status_tool(mock_manager)
        result = await tool.execute(GitStatusInput(), NoteContext())

        assert result.branch == "main"
        assert result.is_clean is True

    @pytest.mark.asyncio
    async def test_git_commit_tool_flow(self) -> None:
        """Test git commit tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.commit_with_scope.return_value = "abc123def"

        tool = make_git_commit_tool(mock_manager)
        result = await tool.execute(
            GitCommitInput(
                workflow_phase="implementation",
                cycle_number=1,
                sub_phase="green",
                commit_type="feat",
                message="implement feature",
            ),
            NoteContext(),
        )

        assert result.commit_hash == "abc123def"
        mock_manager.commit_with_scope.assert_called_once_with(
            workflow_phase="implementation",
            message="implement feature",
            note_context=ANY,
            sub_phase="green",
            cycle_number=1,
            commit_type="feat",
            files=None,
            skip_paths=frozenset(),
            issue_number=None,
        )

    @pytest.mark.asyncio
    async def test_git_restore_tool_flow(self) -> None:
        """Test git restore tool complete flow."""
        mock_manager = make_mock_git_manager()

        tool = make_git_restore_tool(mock_manager)
        result = await tool.execute(GitRestoreInput(files=["a.py"], source="HEAD"), NoteContext())

        assert result.success is True
        assert result.files_count == 1
        mock_manager.restore.assert_called_once_with(
            files=["a.py"], note_context=ANY, source="HEAD"
        )

    @pytest.mark.asyncio
    async def test_git_checkout_tool_flow(self) -> None:
        """Test git checkout tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.get_current_branch.return_value = "main"

        tool = make_git_checkout_tool(mock_manager)
        result = await tool.execute(GitCheckoutInput(branch="feature/test"), NoteContext())

        assert result.branch == "feature/test"
        mock_manager.checkout.assert_called_once_with("feature/test")

    @pytest.mark.asyncio
    async def test_git_push_tool_flow(self) -> None:
        """Test git push tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.get_status.return_value = {
            "branch": "feature/test",
            "is_clean": True,
            "untracked_files": [],
            "modified_files": [],
        }

        tool = make_git_push_tool(mock_manager)
        result = await tool.execute(GitPushInput(), NoteContext())

        assert result.branch == "feature/test"
        mock_manager.push.assert_called_once_with(set_upstream=False)

    @pytest.mark.asyncio
    async def test_git_merge_tool_flow(self) -> None:
        """Test git merge tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.get_status.return_value = {
            "branch": "main",
            "is_clean": True,
            "untracked_files": [],
            "modified_files": [],
        }

        tool = make_git_merge_tool(mock_manager)
        result = await tool.execute(GitMergeInput(branch="feature/test"), NoteContext())

        assert result.source_branch == "feature/test"
        mock_manager.merge.assert_called_once_with("feature/test", ANY)

    @pytest.mark.asyncio
    async def test_git_delete_branch_tool_flow(self) -> None:
        """Test git delete branch tool complete flow."""
        mock_manager = make_mock_git_manager()

        tool = make_git_delete_branch_tool(mock_manager)
        result = await tool.execute(GitDeleteBranchInput(branch="feature/old"), NoteContext())

        assert result.branch == "feature/old"
        mock_manager.delete_branch.assert_called_once_with(
            "feature/old", ANY, force=False, mode="both"
        )

    @pytest.mark.asyncio
    async def test_git_stash_tool_push_flow(self) -> None:
        """Test git stash push tool complete flow."""
        mock_manager = make_mock_git_manager()

        tool = make_git_stash_tool(mock_manager)
        result = await tool.execute(GitStashInput(action="push", message="WIP"), NoteContext())

        assert result.message == "WIP"
        mock_manager.stash.assert_called_once_with(message="WIP", include_untracked=False)

    @pytest.mark.asyncio
    async def test_git_stash_tool_pop_flow(self) -> None:
        """Test git stash pop tool complete flow."""
        mock_manager = make_mock_git_manager()

        tool = make_git_stash_tool(mock_manager)
        result = await tool.execute(GitStashInput(action="pop"), NoteContext())

        assert result.action == "pop"
        mock_manager.stash_pop.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_git_stash_tool_list_flow(self) -> None:
        """Test git stash list tool complete flow."""
        mock_manager = make_mock_git_manager()
        mock_manager.stash_list.return_value = ["stash@{0}: WIP on main"]

        tool = make_git_stash_tool(mock_manager)
        result = await tool.execute(GitStashInput(action="list"), NoteContext())

        assert "stash@{0}" in result.stashes[0]


class TestQualityToolsIntegration:
    """Integration tests for Quality tools."""

    @pytest.mark.asyncio
    async def test_run_quality_gates_tool_flow(self) -> None:
        """Test quality gates tool complete flow."""
        mock_manager = make_mock_qa_manager()

        tool = make_run_quality_gates_tool(mock_manager)
        result = await tool.execute(
            RunQualityGatesInput(scope="files", files=["test.py"]), NoteContext()
        )

        assert result.overall_pass is True
        assert len(result.gates) > 0
        assert result.gates[0].passed is True


class TestDevelopmentToolsIntegration:
    """Integration tests for Development tools."""

    @pytest.mark.asyncio
    async def test_health_check_tool_flow(self) -> None:
        """Test health check tool complete flow."""
        tool = HealthCheckTool()
        result = await tool.execute(HealthCheckInput(), NoteContext())

        assert result.status == "healthy"


class TestGitHubToolsIntegration:
    """Integration tests for GitHub tools (require mocking at tool level)."""

    @pytest.mark.asyncio
    async def test_create_issue_tool_flow(self) -> None:
        """Test create issue tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.create_issue.return_value = {
            "number": 42,
            "url": "https://github.com/test/repo/issues/42",
            "title": "Test Issue",
        }
        mock_manager.get_issue.return_value = IssueReadModel(
            number=42,
            url="https://github.com/test/repo/issues/42",
            title="Test Issue",
            body="## Problem\n\nTest body.",
            state="open",
            labels=["type:feature", "scope:mcp-server", "priority:medium", "phase:research"],
            milestone=None,
            assignees=[],
            created_at="2026-06-14T23:11:11Z",
            updated_at="2026-06-14T23:11:11Z",
            closed_at=None,
            author="test-user",
        )

        tool = make_create_issue_tool(mock_manager)
        result = await tool.execute(
            CreateIssueInput(
                issue_type="feature",
                title="Test Issue",
                priority="medium",
                scope="mcp-server",
                body="## Problem\n\nTest body.",
            ),
            NoteContext(),
        )

        assert result.number == 42
        assert result.title == "Test Issue"

    @pytest.mark.asyncio
    async def test_add_labels_tool_flow(self) -> None:
        """Test add labels tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.add_labels.return_value = ["bug", "priority:high"]

        tool = make_add_labels_tool(mock_manager)
        result = await tool.execute(
            AddLabelsInput(issue_number=42, labels=["bug", "priority:high"]), NoteContext()
        )

        assert result.issue_number == 42
        assert result.labels == ["bug", "priority:high"]


class TestToolSchemas:
    """Test that all tools have valid schemas."""

    def test_all_git_tools_have_schemas(self) -> None:
        """Verify all Git tools have input schemas."""
        tools = [
            make_create_branch_tool(),
            make_git_checkout_tool(),
            make_git_stash_tool(),
            make_git_status_tool(),
            make_git_restore_tool(),
            make_git_commit_tool(),
            make_git_merge_tool(),
            make_git_push_tool(),
            make_git_delete_branch_tool(),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_all_quality_tools_have_schemas(self) -> None:
        """Verify all Quality tools have input schemas."""
        tools = [
            make_run_quality_gates_tool(),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_all_dev_tools_have_schemas(self) -> None:
        tools = [
            HealthCheckTool(),
            RunTestsTool(runner=PytestRunner()),
        ]
        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_github_tools_have_schemas_with_mock(self) -> None:
        """Verify all GitHub tools have input schemas (with mocked manager)."""
        mock_manager = MagicMock()
        tools = [
            make_create_issue_tool(mock_manager),
            make_add_labels_tool(mock_manager),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"


class TestToolNames:
    """Test that all tools have unique names."""

    def test_all_core_tool_names_unique(self) -> None:
        """Verify all core tools have unique names."""
        names = [tool.name for tool in make_core_tools()]
        assert len(names) == len(set(names)), f"Duplicate tool names found: {names}"

    def test_github_tool_names_with_mock(self) -> None:
        """Verify GitHub tools have unique names (with mocked manager)."""
        mock_manager = MagicMock()
        tools = [
            make_create_issue_tool(mock_manager),
            make_add_labels_tool(mock_manager),
        ]

        names = [tool.name for tool in tools]
        assert len(names) == len(set(names)), f"Duplicate tool names found: {names}"

    def test_all_core_tools_have_descriptions(self) -> None:
        """Verify all core tools have descriptions."""
        for tool in make_core_tools():
            assert tool.description, f"{tool.name} missing description"
            assert len(tool.description) > 10, f"{tool.name} description too short"

    def test_github_tools_have_descriptions_with_mock(self) -> None:
        """Verify GitHub tools have descriptions (with mocked manager)."""
        mock_manager = MagicMock()
        tools = [
            make_create_issue_tool(mock_manager),
            make_add_labels_tool(mock_manager),
        ]

        for tool in tools:
            assert tool.description, f"{tool.name} missing description"
            assert len(tool.description) > 10, f"{tool.name} description too short"
