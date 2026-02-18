"""Integration tests for all MCP server tools.

Phase 1.3: Verify all tools are operational and return expected results.
These tests use mocks but test the full flow from Tool -> Manager -> Adapter.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.tools.code_tools import CreateFileInput, CreateFileTool

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
from mcp_server.tools.pr_tools import CreatePRInput, CreatePRTool

# Quality Tools
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.validation_tools import (
    ValidateDTOInput,
    ValidateDTOTool,
    ValidationInput,
    ValidationTool,
)


class TestGitToolsIntegration:
    """Integration tests for all Git tools."""

    @pytest.mark.asyncio
    async def test_create_branch_tool_flow(self) -> None:
        """Test create branch tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.is_clean.return_value = True

            tool = CreateBranchTool()
            result = await tool.execute(
                CreateBranchInput(name="test-feature", branch_type="feature", base_branch="HEAD")
            )

            assert "feature/test-feature" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_git_status_tool_flow(self) -> None:
        """Test git status tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.get_status.return_value = {
                "branch": "main",
                "is_clean": True,
                "untracked_files": [],
                "modified_files": [],
            }

            tool = GitStatusTool()
            result = await tool.execute(GitStatusInput())

            assert "Branch: main" in result.content[0]["text"]
            assert "Clean: True" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_git_commit_tool_flow(self) -> None:
        """Test git commit tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.commit.return_value = "abc123def"

            tool = GitCommitTool()
            result = await tool.execute(
                GitCommitInput(
                    workflow_phase="tdd",
                    cycle_number=1,
                    sub_phase="green",
                    message="implement feature",
                )
            )

            assert "abc123def" in result.content[0]["text"]
            mock_adapter.return_value.commit.assert_called_with(
                "feat(P_TDD_SP_C1_GREEN): implement feature",
                files=None,
            )

    @pytest.mark.asyncio
    async def test_git_restore_tool_flow(self) -> None:
        """Test git restore tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitRestoreTool()
            result = await tool.execute(GitRestoreInput(files=["a.py"], source="HEAD"))

            assert "Restored" in result.content[0]["text"]
            mock_adapter.return_value.restore.assert_called_with(files=["a.py"], source="HEAD")

    @pytest.mark.asyncio
    async def test_git_checkout_tool_flow(self) -> None:
        """Test git checkout tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitCheckoutTool()
            result = await tool.execute(GitCheckoutInput(branch="feature/test"))

            assert "feature/test" in result.content[0]["text"]
            mock_adapter.return_value.checkout.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_push_tool_flow(self) -> None:
        """Test git push tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.get_status.return_value = {"branch": "feature/test"}

            tool = GitPushTool()
            result = await tool.execute(GitPushInput())

            assert "feature/test" in result.content[0]["text"]
            mock_adapter.return_value.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_merge_tool_flow(self) -> None:
        """Test git merge tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.is_clean.return_value = True
            mock_adapter.return_value.get_status.return_value = {"branch": "main"}

            tool = GitMergeTool()
            result = await tool.execute(GitMergeInput(branch="feature/test"))

            assert "feature/test" in result.content[0]["text"]
            mock_adapter.return_value.merge.assert_called_with("feature/test")

    @pytest.mark.asyncio
    async def test_git_delete_branch_tool_flow(self) -> None:
        """Test git delete branch tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitDeleteBranchTool()
            result = await tool.execute(GitDeleteBranchInput(branch="feature/old"))

            assert "feature/old" in result.content[0]["text"]
            mock_adapter.return_value.delete_branch.assert_called_with("feature/old", force=False)

    @pytest.mark.asyncio
    async def test_git_stash_tool_push_flow(self) -> None:
        """Test git stash push tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitStashTool()
            result = await tool.execute(GitStashInput(action="push", message="WIP"))

            assert "WIP" in result.content[0]["text"]
            mock_adapter.return_value.stash.assert_called_with(
                message="WIP",
                include_untracked=False,
            )

    @pytest.mark.asyncio
    async def test_git_stash_tool_pop_flow(self) -> None:
        """Test git stash pop tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitStashTool()
            result = await tool.execute(GitStashInput(action="pop"))

            assert "Applied" in result.content[0]["text"]
            mock_adapter.return_value.stash_pop.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_stash_tool_list_flow(self) -> None:
        """Test git stash list tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.stash_list.return_value = ["stash@{0}: WIP on main"]

            tool = GitStashTool()
            result = await tool.execute(GitStashInput(action="list"))

            assert "stash@{0}" in result.content[0]["text"]


class TestQualityToolsIntegration:
    """Integration tests for Quality tools."""

    @pytest.mark.asyncio
    async def test_run_quality_gates_tool_flow(self) -> None:
        """Test quality gates tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": True,
            "gates": [{"name": "Linting", "passed": True, "score": "10/10"}],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["test.py"]))

        # Content[0] is native JSON, content[1] is text fallback
        assert result.content[0]["type"] == "json"
        data = result.content[0]["json"]
        assert data["overall_pass"] is True
        assert "text_output" in data

    @pytest.mark.asyncio
    async def test_validation_tool_flow(self) -> None:
        """Test architecture validation tool complete flow."""
        tool = ValidationTool()
        result = await tool.execute(ValidationInput(scope="all"))

        # Should return validation results
        assert result.content is not None

    @pytest.mark.asyncio
    async def test_validate_dto_tool_flow(self) -> None:
        """Test DTO validation tool complete flow."""
        mock_content = (
            "from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass TestDTO:\n    pass"
        )
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=mock_content),
        ):
            tool = ValidateDTOTool()
            result = await tool.execute(ValidateDTOInput(file_path="backend/dtos/test.py"))

            assert result.is_error is False
            assert "DTO validation passed" in result.content[0]["text"]


class TestDevelopmentToolsIntegration:
    """Integration tests for Development tools."""

    @pytest.mark.asyncio
    async def test_health_check_tool_flow(self) -> None:
        """Test health check tool complete flow."""
        tool = HealthCheckTool()
        result = await tool.execute(HealthCheckInput())

        result_text = result.content[0]["text"].lower()
        assert "healthy" in result_text or "ok" in result_text

    @pytest.mark.asyncio
    async def test_create_file_tool_flow(self) -> None:
        """Test create file tool complete flow."""
        with patch("pathlib.Path.mkdir"), patch("builtins.open", MagicMock()):
            tool = CreateFileTool()
            result = await tool.execute(
                CreateFileInput(path="test/file.py", content="# Test content")
            )

            assert result.content is not None


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

        tool = CreateIssueTool(manager=mock_manager)
        result = await tool.execute(CreateIssueInput(title="Test Issue", body="Test body"))

        assert "42" in result.content[0]["text"] or "issue" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_create_pr_tool_flow(self) -> None:
        """Test create PR tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.create_pr.return_value = {
            "number": 99,
            "url": "https://github.com/test/repo/pull/99",
        }

        tool = CreatePRTool(manager=mock_manager)
        result = await tool.execute(
            CreatePRInput(title="Test PR", body="Test body", head="feature/test", base="main")
        )

        assert "99" in result.content[0]["text"] or "pr" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_add_labels_tool_flow(self) -> None:
        """Test add labels tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.add_labels.return_value = ["bug", "priority:high"]

        tool = AddLabelsTool(manager=mock_manager)
        result = await tool.execute(
            AddLabelsInput(issue_number=42, labels=["bug", "priority:high"])
        )

        assert result.content is not None


class TestToolSchemas:
    """Test that all tools have valid schemas."""

    def test_all_git_tools_have_schemas(self) -> None:
        """Verify all Git tools have input schemas."""
        tools = [
            CreateBranchTool(),
            GitCheckoutTool(),
            GitStashTool(),
            GitStatusTool(),
            GitRestoreTool(),
            GitCommitTool(),
            GitMergeTool(),
            GitPushTool(),
            GitDeleteBranchTool(),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_all_quality_tools_have_schemas(self) -> None:
        """Verify all Quality tools have input schemas."""
        tools = [
            RunQualityGatesTool(),
            ValidationTool(),
            ValidateDTOTool(),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_all_dev_tools_have_schemas(self) -> None:
        """Verify all Development tools have input schemas."""
        tools = [
            HealthCheckTool(),
            RunTestsTool(),
            CreateFileTool(),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_github_tools_have_schemas_with_mock(self) -> None:
        """Verify all GitHub tools have input schemas (with mocked manager)."""
        mock_manager = MagicMock()
        tools = [
            CreateIssueTool(manager=mock_manager),
            CreatePRTool(manager=mock_manager),
            AddLabelsTool(manager=mock_manager),
        ]

        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or not schema, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"


class TestToolNames:
    """Test that all tools have unique names."""

    def test_all_core_tool_names_unique(self) -> None:
        """Verify all core tools have unique names."""
        tools = [
            CreateBranchTool(),
            GitCheckoutTool(),
            GitStashTool(),
            GitStatusTool(),
            GitRestoreTool(),
            GitCommitTool(),
            GitMergeTool(),
            GitPushTool(),
            GitDeleteBranchTool(),
            RunQualityGatesTool(),
            ValidationTool(),
            ValidateDTOTool(),
            HealthCheckTool(),
            RunTestsTool(),
            CreateFileTool(),
        ]

        names = [tool.name for tool in tools]
        assert len(names) == len(set(names)), f"Duplicate tool names found: {names}"

    def test_github_tool_names_with_mock(self) -> None:
        """Verify GitHub tools have unique names (with mocked manager)."""
        mock_manager = MagicMock()
        tools = [
            CreateIssueTool(manager=mock_manager),
            CreatePRTool(manager=mock_manager),
            AddLabelsTool(manager=mock_manager),
        ]

        names = [tool.name for tool in tools]
        assert len(names) == len(set(names)), f"Duplicate tool names found: {names}"

    def test_all_core_tools_have_descriptions(self) -> None:
        """Verify all core tools have descriptions."""
        tools = [
            CreateBranchTool(),
            GitCheckoutTool(),
            GitStashTool(),
            GitStatusTool(),
            GitRestoreTool(),
            GitCommitTool(),
            GitMergeTool(),
            GitPushTool(),
            GitDeleteBranchTool(),
            RunQualityGatesTool(),
            ValidationTool(),
            ValidateDTOTool(),
            HealthCheckTool(),
            RunTestsTool(),
            CreateFileTool(),
        ]

        for tool in tools:
            assert tool.description, f"{tool.name} missing description"
            assert len(tool.description) > 10, f"{tool.name} description too short"

    def test_github_tools_have_descriptions_with_mock(self) -> None:
        """Verify GitHub tools have descriptions (with mocked manager)."""
        mock_manager = MagicMock()
        tools = [
            CreateIssueTool(manager=mock_manager),
            CreatePRTool(manager=mock_manager),
            AddLabelsTool(manager=mock_manager),
        ]

        for tool in tools:
            assert tool.description, f"{tool.name} missing description"
            assert len(tool.description) > 10, f"{tool.name} description too short"
