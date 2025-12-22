"""Tests for InitializeProjectTool."""
from unittest.mock import Mock
import pytest

from mcp_server.state.project import ProjectSummary, SubIssueMetadata
from mcp_server.tools.project_tools import (
    InitializeProjectInput,
    InitializeProjectTool,
)


class TestInitializeProjectTool:
    """Test InitializeProjectTool MCP wrapper."""

    def test_tool_attributes(self) -> None:
        """Test tool has correct name and description."""
        tool = InitializeProjectTool()
        assert tool.name == "initialize_project"
        assert "Initialize a project" in tool.description
        assert tool.args_model == InitializeProjectInput

    def test_input_schema(self) -> None:
        """Test input schema is properly generated."""
        tool = InitializeProjectTool()
        schema = tool.input_schema
        assert "properties" in schema
        assert "project_title" in schema["properties"]
        assert "phases" in schema["properties"]

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful project initialization."""
        # Setup mock manager
        mock_manager = Mock()
        mock_summary = ProjectSummary(
            project_id="test-project-123",
            milestone_id=10,
            parent_issue={
                "number": 100,
                "url": "https://github.com/org/repo/issues/100"
            },
            sub_issues={
                "A": SubIssueMetadata(
                    issue_number=101,
                    url="https://github.com/org/repo/issues/101",
                    depends_on=[],
                    blocks=["B"],
                    status="open",
                )
            },
            dependency_graph={"A": ["B"], "B": []},
        )
        mock_manager.initialize_project.return_value = mock_summary

        tool = InitializeProjectTool(manager=mock_manager)

        # Execute
        params = InitializeProjectInput(
            project_title="Test Project",
            phases=[
                {
                    "phase_id": "A",
                    "title": "Phase A",
                    "depends_on": [],
                    "blocks": ["B"],
                },
                {
                    "phase_id": "B",
                    "title": "Phase B",
                    "depends_on": ["A"],
                    "blocks": [],
                },
            ],
        )
        result = await tool.execute(params)

        # Verify
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert "test-project-123" in content_text
        assert "#100" in content_text
        assert "#101" in content_text
        mock_manager.initialize_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_invalid_phase_spec(self) -> None:
        """Test error handling for invalid phase specification."""
        mock_manager = Mock()
        tool = InitializeProjectTool(manager=mock_manager)

        # Invalid phase: missing required fields
        params = InitializeProjectInput(
            project_title="Test Project",
            phases=[{"invalid": "data"}],
        )
        result = await tool.execute(params)

        # Verify error
        assert result.is_error is True
        content_text = result.content[0]["text"]
        assert "Invalid input" in content_text
        mock_manager.initialize_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_circular_dependency_error(self) -> None:
        """Test error handling for circular dependencies."""
        mock_manager = Mock()
        mock_manager.initialize_project.side_effect = ValueError(
            "Circular dependency detected: A → B → A"
        )
        tool = InitializeProjectTool(manager=mock_manager)

        params = InitializeProjectInput(
            project_title="Test Project",
            phases=[
                {
                    "phase_id": "A",
                    "title": "Phase A",
                    "depends_on": ["B"],
                    "blocks": [],
                },
                {
                    "phase_id": "B",
                    "title": "Phase B",
                    "depends_on": ["A"],
                    "blocks": [],
                },
            ],
        )
        result = await tool.execute(params)

        # Verify error
        assert result.is_error is True
        content_text = result.content[0]["text"]
        assert "Invalid input" in content_text
        assert "Circular dependency" in content_text

    @pytest.mark.asyncio
    async def test_execute_github_api_error(self) -> None:
        """Test error handling for GitHub API failures."""
        mock_manager = Mock()
        mock_manager.initialize_project.side_effect = RuntimeError(
            "GitHub API Error: Rate limit exceeded"
        )
        tool = InitializeProjectTool(manager=mock_manager)

        params = InitializeProjectInput(
            project_title="Test Project",
            phases=[
                {
                    "phase_id": "A",
                    "title": "Phase A",
                    "depends_on": [],
                    "blocks": [],
                }
            ],
        )
        result = await tool.execute(params)

        # Verify error
        assert result.is_error is True
        content_text = result.content[0]["text"]
        assert "Runtime error" in content_text
        assert "Rate limit" in content_text

    @pytest.mark.asyncio
    async def test_execute_no_manager_configured(self) -> None:
        """Test error when ProjectManager not configured."""
        tool = InitializeProjectTool(manager=None)

        params = InitializeProjectInput(
            project_title="Test Project",
            phases=[
                {
                    "phase_id": "A",
                    "title": "Phase A",
                    "depends_on": [],
                    "blocks": [],
                }
            ],
        )
        result = await tool.execute(params)

        # Verify error
        assert result.is_error is True
        content_text = result.content[0]["text"]
        assert "ProjectManager not configured" in content_text

    @pytest.mark.asyncio
    async def test_execute_with_parent_issue_number(self) -> None:
        """Test initialization with existing parent issue."""
        mock_manager = Mock()
        mock_summary = ProjectSummary(
            project_id="test-project-456",
            milestone_id=11,
            parent_issue={
                "number": 18,
                "url": "https://github.com/org/repo/issues/18"
            },
            sub_issues={},
            dependency_graph={},
        )
        mock_manager.initialize_project.return_value = mock_summary

        tool = InitializeProjectTool(manager=mock_manager)

        params = InitializeProjectInput(
            project_title="Test Project",
            phases=[
                {
                    "phase_id": "A",
                    "title": "Phase A",
                    "depends_on": [],
                    "blocks": [],
                }
            ],
            parent_issue_number=18,
        )
        result = await tool.execute(params)

        # Verify
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert "#18" in content_text

        # Verify ProjectSpec had parent_issue_number=18
        call_args = mock_manager.initialize_project.call_args
        project_spec = call_args[0][0]
        assert project_spec.parent_issue_number == 18

    @pytest.mark.asyncio
    async def test_format_summary_with_dependencies(self) -> None:
        """Test summary formatting includes dependency information."""
        mock_manager = Mock()
        mock_summary = ProjectSummary(
            project_id="test-complex-789",
            milestone_id=12,
            parent_issue={
                "number": 200,
                "url": "https://github.com/org/repo/issues/200"
            },
            sub_issues={
                "A": SubIssueMetadata(
                    issue_number=201,
                    url="https://github.com/org/repo/issues/201",
                    depends_on=[],
                    blocks=["B", "C"],
                    status="open",
                ),
                "B": SubIssueMetadata(
                    issue_number=202,
                    url="https://github.com/org/repo/issues/202",
                    depends_on=["A"],
                    blocks=[],
                    status="open",
                ),
            },
            dependency_graph={"A": ["B", "C"], "B": [], "C": []},
        )
        mock_manager.initialize_project.return_value = mock_summary

        tool = InitializeProjectTool(manager=mock_manager)

        params = InitializeProjectInput(
            project_title="Complex Project",
            phases=[
                {
                    "phase_id": "A",
                    "title": "Phase A",
                    "depends_on": [],
                    "blocks": ["B", "C"],
                },
                {
                    "phase_id": "B",
                    "title": "Phase B",
                    "depends_on": ["A"],
                    "blocks": [],
                },
                {
                    "phase_id": "C",
                    "title": "Phase C",
                    "depends_on": ["A"],
                    "blocks": [],
                },
            ],
        )
        result = await tool.execute(params)

        # Verify formatting
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert "Depends on: A" in content_text
        assert "Blocks: B, C" in content_text
        assert "Dependency Graph:" in content_text
        assert "**A** blocks: B, C" in content_text
