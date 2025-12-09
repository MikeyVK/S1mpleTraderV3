"""Integration tests for all MCP server tools.

Phase 1.3: Verify all tools are operational and return expected results.
These tests use mocks but test the full flow from Tool -> Manager -> Adapter.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Git Tools
from mcp_server.tools.git_tools import (
    CreateBranchTool,
    GitStatusTool,
    GitCommitTool,
    GitCheckoutTool,
    GitPushTool,
    GitMergeTool,
    GitDeleteBranchTool,
    GitStashTool,
)

# Quality Tools
from mcp_server.tools.quality_tools import RunQualityGatesTool
from mcp_server.tools.docs_tools import ValidateDocTool
from mcp_server.tools.validation_tools import ValidationTool, ValidateDTOTool

# Development Tools
from mcp_server.tools.health_tools import HealthCheckTool
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.code_tools import CreateFileTool


class TestGitToolsIntegration:
    """Integration tests for all Git tools."""

    @pytest.mark.asyncio
    async def test_create_branch_tool_flow(self) -> None:
        """Test create branch tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.is_clean.return_value = True
            
            tool = CreateBranchTool()
            result = await tool.execute(name="test-feature", branch_type="feature")
            
            assert "feature/test-feature" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_git_status_tool_flow(self) -> None:
        """Test git status tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.get_status.return_value = {
                "branch": "main",
                "is_clean": True,
                "untracked_files": [],
                "modified_files": []
            }
            
            tool = GitStatusTool()
            result = await tool.execute()
            
            assert "Branch: main" in result.content[0]["text"]
            assert "Clean: True" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_git_commit_tool_flow(self) -> None:
        """Test git commit tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.commit.return_value = "abc123def"
            
            tool = GitCommitTool()
            result = await tool.execute(phase="green", message="implement feature")
            
            assert "abc123def" in result.content[0]["text"]
            mock_adapter.return_value.commit.assert_called_with("feat: implement feature")

    @pytest.mark.asyncio
    async def test_git_checkout_tool_flow(self) -> None:
        """Test git checkout tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitCheckoutTool()
            result = await tool.execute(branch="feature/test")
            
            assert "feature/test" in result.content[0]["text"]
            mock_adapter.return_value.checkout.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_push_tool_flow(self) -> None:
        """Test git push tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.get_status.return_value = {"branch": "feature/test"}
            
            tool = GitPushTool()
            result = await tool.execute()
            
            assert "feature/test" in result.content[0]["text"]
            mock_adapter.return_value.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_merge_tool_flow(self) -> None:
        """Test git merge tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.is_clean.return_value = True
            mock_adapter.return_value.get_status.return_value = {"branch": "main"}
            
            tool = GitMergeTool()
            result = await tool.execute(branch="feature/test")
            
            assert "feature/test" in result.content[0]["text"]
            mock_adapter.return_value.merge.assert_called_with("feature/test")

    @pytest.mark.asyncio
    async def test_git_delete_branch_tool_flow(self) -> None:
        """Test git delete branch tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitDeleteBranchTool()
            result = await tool.execute(branch="feature/old")
            
            assert "feature/old" in result.content[0]["text"]
            mock_adapter.return_value.delete_branch.assert_called_with(
                "feature/old", force=False
            )

    @pytest.mark.asyncio
    async def test_git_stash_tool_push_flow(self) -> None:
        """Test git stash push tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitStashTool()
            result = await tool.execute(action="push", message="WIP")
            
            assert "WIP" in result.content[0]["text"]
            mock_adapter.return_value.stash.assert_called_with(message="WIP")

    @pytest.mark.asyncio
    async def test_git_stash_tool_pop_flow(self) -> None:
        """Test git stash pop tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            tool = GitStashTool()
            result = await tool.execute(action="pop")
            
            assert "Applied" in result.content[0]["text"]
            mock_adapter.return_value.stash_pop.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_stash_tool_list_flow(self) -> None:
        """Test git stash list tool complete flow."""
        with patch("mcp_server.managers.git_manager.GitAdapter") as mock_adapter:
            mock_adapter.return_value.stash_list.return_value = [
                "stash@{0}: WIP on main"
            ]
            
            tool = GitStashTool()
            result = await tool.execute(action="list")
            
            assert "stash@{0}" in result.content[0]["text"]


class TestQualityToolsIntegration:
    """Integration tests for Quality tools."""

    @pytest.mark.asyncio
    async def test_run_quality_gates_tool_flow(self) -> None:
        """Test quality gates tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": True,
            "gates": [{"name": "Linting", "passed": True, "score": "10/10"}]
        }
        
        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(files=["test.py"])
        
        assert "Pass" in result.content[0]["text"] or "pass" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_validate_doc_tool_flow(self) -> None:
        """Test validate doc tool complete flow."""
        mock_manager = MagicMock()
        mock_manager.validate_structure.return_value = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        tool = ValidateDocTool(manager=mock_manager)
        result = await tool.execute(
            content="# Title\n\n## Section",
            template_type="design"
        )
        
        # Tool returns validation result
        assert result.content is not None

    @pytest.mark.asyncio
    async def test_validation_tool_flow(self) -> None:
        """Test architecture validation tool complete flow."""
        tool = ValidationTool()
        result = await tool.execute(scope="all")
        
        # Should return validation results
        assert result.content is not None

    @pytest.mark.asyncio
    async def test_validate_dto_tool_flow(self) -> None:
        """Test DTO validation tool complete flow."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass TestDTO:\n    pass"):
                tool = ValidateDTOTool()
                result = await tool.execute(file_path="backend/dtos/test.py")
                
                assert result.content is not None


class TestDevelopmentToolsIntegration:
    """Integration tests for Development tools."""

    @pytest.mark.asyncio
    async def test_health_check_tool_flow(self) -> None:
        """Test health check tool complete flow."""
        tool = HealthCheckTool()
        result = await tool.execute()
        
        assert "healthy" in result.content[0]["text"].lower() or "ok" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_create_file_tool_flow(self) -> None:
        """Test create file tool complete flow."""
        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                tool = CreateFileTool()
                result = await tool.execute(
                    path="test/file.py",
                    content="# Test content"
                )
                
                assert result.content is not None


class TestGitHubToolsIntegration:
    """Integration tests for GitHub tools (require mocking at tool level)."""

    @pytest.mark.asyncio
    async def test_create_issue_tool_flow(self) -> None:
        """Test create issue tool complete flow."""
        # Import here to avoid failure when no GITHUB_TOKEN
        from mcp_server.tools.issue_tools import CreateIssueTool
        
        mock_manager = MagicMock()
        mock_manager.create_issue.return_value = {
            "number": 42,
            "url": "https://github.com/test/repo/issues/42"
        }
        
        tool = CreateIssueTool(manager=mock_manager)
        result = await tool.execute(
            title="Test Issue",
            body="Test body"
        )
        
        assert "42" in result.content[0]["text"] or "issue" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_create_pr_tool_flow(self) -> None:
        """Test create PR tool complete flow."""
        from mcp_server.tools.pr_tools import CreatePRTool
        
        mock_manager = MagicMock()
        mock_manager.create_pr.return_value = {
            "number": 99,
            "url": "https://github.com/test/repo/pull/99"
        }
        
        tool = CreatePRTool(manager=mock_manager)
        result = await tool.execute(
            title="Test PR",
            body="Test body",
            head="feature/test",
            base="main"
        )
        
        assert "99" in result.content[0]["text"] or "pr" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_add_labels_tool_flow(self) -> None:
        """Test add labels tool complete flow."""
        from mcp_server.tools.label_tools import AddLabelsTool
        
        mock_manager = MagicMock()
        mock_manager.add_labels.return_value = ["bug", "priority:high"]
        
        tool = AddLabelsTool(manager=mock_manager)
        result = await tool.execute(
            issue_number=42,
            labels=["bug", "priority:high"]
        )
        
        assert result.content is not None


class TestToolSchemas:
    """Test that all tools have valid schemas."""

    def test_all_git_tools_have_schemas(self) -> None:
        """Verify all Git tools have input schemas."""
        tools = [
            CreateBranchTool(),
            GitStatusTool(),
            GitCommitTool(),
            GitCheckoutTool(),
            GitPushTool(),
            GitMergeTool(),
            GitDeleteBranchTool(),
            GitStashTool(),
        ]
        
        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or schema == {}, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_all_quality_tools_have_schemas(self) -> None:
        """Verify all Quality tools have input schemas."""
        tools = [
            RunQualityGatesTool(),
            ValidateDocTool(),
            ValidationTool(),
            ValidateDTOTool(),
        ]
        
        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or schema == {}, f"{tool.name} missing schema"
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
            assert schema is not None or schema == {}, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"

    def test_github_tools_have_schemas_with_mock(self) -> None:
        """Verify all GitHub tools have input schemas (with mocked manager)."""
        from mcp_server.tools.issue_tools import CreateIssueTool
        from mcp_server.tools.pr_tools import CreatePRTool
        from mcp_server.tools.label_tools import AddLabelsTool
        
        mock_manager = MagicMock()
        tools = [
            CreateIssueTool(manager=mock_manager),
            CreatePRTool(manager=mock_manager),
            AddLabelsTool(manager=mock_manager),
        ]
        
        for tool in tools:
            schema = tool.input_schema
            assert schema is not None or schema == {}, f"{tool.name} missing schema"
            assert isinstance(schema, dict), f"{tool.name} schema not a dict"


class TestToolNames:
    """Test that all tools have unique names."""

    def test_all_core_tool_names_unique(self) -> None:
        """Verify all core tools have unique names."""
        tools = [
            CreateBranchTool(),
            GitStatusTool(),
            GitCommitTool(),
            GitCheckoutTool(),
            GitPushTool(),
            GitMergeTool(),
            GitDeleteBranchTool(),
            GitStashTool(),
            RunQualityGatesTool(),
            ValidateDocTool(),
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
        from mcp_server.tools.issue_tools import CreateIssueTool
        from mcp_server.tools.pr_tools import CreatePRTool
        from mcp_server.tools.label_tools import AddLabelsTool
        
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
            GitStatusTool(),
            GitCommitTool(),
            GitCheckoutTool(),
            GitPushTool(),
            GitMergeTool(),
            GitDeleteBranchTool(),
            GitStashTool(),
            RunQualityGatesTool(),
            ValidateDocTool(),
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
        from mcp_server.tools.issue_tools import CreateIssueTool
        from mcp_server.tools.pr_tools import CreatePRTool
        from mcp_server.tools.label_tools import AddLabelsTool
        
        mock_manager = MagicMock()
        tools = [
            CreateIssueTool(manager=mock_manager),
            CreatePRTool(manager=mock_manager),
            AddLabelsTool(manager=mock_manager),
        ]
        
        for tool in tools:
            assert tool.description, f"{tool.name} missing description"
            assert len(tool.description) > 10, f"{tool.name} description too short"
