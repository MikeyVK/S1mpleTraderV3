"""RED tests for ValidateProjectStructureTool.

Tests validation of project structure against GitHub API:
1. Read .st3/projects.json
2. Query GitHub for milestone/issues
3. Detect discrepancies (missing issues, circular deps, label mismatches)
4. Return ValidationResult with errors/warnings
"""
import json
from pathlib import Path
from unittest.mock import Mock
import pytest

from mcp_server.state.project import (
    ProjectMetadata,
    SubIssueMetadata,
    ValidationError,
    ValidationResult,
)
from mcp_server.tools.project_tools import ValidateProjectStructureTool


@pytest.mark.asyncio
class TestValidateProjectStructureTool:
    """Test ValidateProjectStructureTool."""

    def test_tool_attributes(self) -> None:
        """Test tool has correct name and description."""
        tool = ValidateProjectStructureTool()
        assert tool.name == "validate_project_structure"
        assert "validate" in tool.description.lower()
        assert "project" in tool.description.lower()

    def test_input_schema(self) -> None:
        """Test tool has correct input schema."""
        tool = ValidateProjectStructureTool()
        schema = tool.input_schema
        assert "project_id" in schema["properties"]
        assert schema["properties"]["project_id"]["type"] == "string"
        assert "project_id" in schema["required"]

    async def test_valid_project_structure(self, tmp_path: Path) -> None:
        """Test validation succeeds for valid project."""
        # Setup: Create .st3/projects.json
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        
        metadata = ProjectMetadata(
            project_id="project-test",
            parent_issue={"number": 100, "url": "https://github.com/org/repo/issues/100"},
            milestone_id=10,
            phases={
                "A": SubIssueMetadata(
                    issue_number=101,
                    url="https://github.com/org/repo/issues/101",
                    depends_on=[],
                    blocks=["B"],
                    status="open"
                ),
                "B": SubIssueMetadata(
                    issue_number=102,
                    url="https://github.com/org/repo/issues/102",
                    depends_on=["A"],
                    blocks=[],
                    status="open"
                )
            }
        )
        
        projects_data = {"projects": {"project-test": metadata.model_dump()}}
        projects_file.write_text(json.dumps(projects_data))

        # Mock GitHub adapter
        mock_adapter = Mock()
        mock_adapter.get_milestone.return_value = {
            "number": 10,
            "title": "Test Milestone",
            "state": "open"
        }
        mock_adapter.get_issue.side_effect = [
            {"number": 100, "state": "open", "labels": [{"name": "parent"}]},
            {"number": 101, "state": "open", "labels": [{"name": "phase:red"}]},
            {"number": 102, "state": "open", "labels": [{"name": "phase:red"}]}
        ]

        # Execute
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        result = await tool.execute({"project_id": "project-test"})

        # Assert
        assert result.is_error is False
        validation_result = ValidationResult.model_validate_json(result.content[0]["text"])
        assert validation_result.valid is True
        assert len(validation_result.errors) == 0

    async def test_missing_project_file(self, tmp_path: Path) -> None:
        """Test validation fails when .st3/projects.json doesn't exist."""
        mock_adapter = Mock()
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        
        result = await tool.execute({"project_id": "nonexistent"})
        
        assert result.is_error is True
        assert "not found" in result.content[0]["text"].lower()

    async def test_missing_project_id(self, tmp_path: Path) -> None:
        """Test validation fails when project_id not in file."""
        # Setup: Create .st3/projects.json with different project
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        projects_file.write_text(json.dumps({"projects": {}}))

        mock_adapter = Mock()
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        
        result = await tool.execute({"project_id": "nonexistent"})
        
        assert result.is_error is True
        assert "project_id" in result.content[0]["text"].lower()

    async def test_missing_milestone_in_github(self, tmp_path: Path) -> None:
        """Test validation detects missing milestone."""
        # Setup: Create .st3/projects.json
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        
        metadata = ProjectMetadata(
            project_id="project-test",
            parent_issue={"number": 100, "url": "https://github.com/org/repo/issues/100"},
            milestone_id=999,  # Non-existent
            phases={}
        )
        
        projects_data = {"projects": {"project-test": metadata.model_dump()}}
        projects_file.write_text(json.dumps(projects_data))

        # Mock GitHub adapter - milestone not found
        mock_adapter = Mock()
        mock_adapter.get_milestone.side_effect = Exception("Milestone not found")
        mock_adapter.get_issue.return_value = {"number": 100, "state": "open", "labels": []}

        # Execute
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        result = await tool.execute({"project_id": "project-test"})

        # Assert
        assert result.is_error is False
        validation_result = ValidationResult.model_validate_json(result.content[0]["text"])
        assert validation_result.valid is False
        assert len(validation_result.errors) == 1
        assert validation_result.errors[0].type == "missing_milestone"
        assert "999" in validation_result.errors[0].message

    async def test_missing_issue_in_github(self, tmp_path: Path) -> None:
        """Test validation detects missing issue."""
        # Setup: Create .st3/projects.json
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        
        metadata = ProjectMetadata(
            project_id="project-test",
            parent_issue={"number": 100, "url": "https://github.com/org/repo/issues/100"},
            milestone_id=10,
            phases={
                "A": SubIssueMetadata(
                    issue_number=999,  # Non-existent
                    url="https://github.com/org/repo/issues/999",
                    depends_on=[],
                    blocks=[],
                    status="open"
                )
            }
        )
        
        projects_data = {"projects": {"project-test": metadata.model_dump()}}
        projects_file.write_text(json.dumps(projects_data))

        # Mock GitHub adapter
        mock_adapter = Mock()
        mock_adapter.get_milestone.return_value = {"number": 10, "state": "open"}
        mock_adapter.get_issue.side_effect = [
            {"number": 100, "state": "open", "labels": []},  # parent
            Exception("Issue not found")  # phase A issue
        ]

        # Execute
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        result = await tool.execute({"project_id": "project-test"})

        # Assert
        assert result.is_error is False
        validation_result = ValidationResult.model_validate_json(result.content[0]["text"])
        assert validation_result.valid is False
        assert len(validation_result.errors) == 1
        assert validation_result.errors[0].type == "missing_issue"
        assert validation_result.errors[0].phase_id == "A"
        assert validation_result.errors[0].issue_number == 999

    async def test_label_mismatch_warning(self, tmp_path: Path) -> None:
        """Test validation warns about label mismatches."""
        # Setup: Create .st3/projects.json
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        
        metadata = ProjectMetadata(
            project_id="project-test",
            parent_issue={"number": 100, "url": "https://github.com/org/repo/issues/100"},
            milestone_id=10,
            phases={
                "A": SubIssueMetadata(
                    issue_number=101,
                    url="https://github.com/org/repo/issues/101",
                    depends_on=[],
                    blocks=[],
                    status="open"
                )
            }
        )
        
        projects_data = {"projects": {"project-test": metadata.model_dump()}}
        projects_file.write_text(json.dumps(projects_data))

        # Mock GitHub adapter - issue has wrong label
        mock_adapter = Mock()
        mock_adapter.get_milestone.return_value = {"number": 10, "state": "open"}
        mock_adapter.get_issue.side_effect = [
            {"number": 100, "state": "open", "labels": []},  # parent
            {"number": 101, "state": "open", "labels": [{"name": "phase:green"}]}  # Should be red
        ]

        # Execute
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        result = await tool.execute({"project_id": "project-test"})

        # Assert
        assert result.is_error is False
        validation_result = ValidationResult.model_validate_json(result.content[0]["text"])
        assert validation_result.valid is True  # Warnings don't fail validation
        assert len(validation_result.warnings) == 1
        assert validation_result.warnings[0].type == "label_mismatch"
        assert validation_result.warnings[0].phase_id == "A"

    async def test_closed_issue_warning(self, tmp_path: Path) -> None:
        """Test validation warns when issue closed but metadata shows open."""
        # Setup: Create .st3/projects.json
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        
        metadata = ProjectMetadata(
            project_id="project-test",
            parent_issue={"number": 100, "url": "https://github.com/org/repo/issues/100"},
            milestone_id=10,
            phases={
                "A": SubIssueMetadata(
                    issue_number=101,
                    url="https://github.com/org/repo/issues/101",
                    depends_on=[],
                    blocks=["B"],
                    status="open"  # Metadata says open
                ),
                "B": SubIssueMetadata(
                    issue_number=102,
                    url="https://github.com/org/repo/issues/102",
                    depends_on=["A"],
                    blocks=[],
                    status="open"
                )
            }
        )
        
        projects_data = {"projects": {"project-test": metadata.model_dump()}}
        projects_file.write_text(json.dumps(projects_data))

        # Mock GitHub adapter - issue A is closed
        mock_adapter = Mock()
        mock_adapter.get_milestone.return_value = {"number": 10, "state": "open"}
        mock_adapter.get_issue.side_effect = [
            {"number": 100, "state": "open", "labels": []},  # parent
            {"number": 101, "state": "closed", "labels": [{"name": "phase:red"}]},  # Phase A closed!
            {"number": 102, "state": "open", "labels": [{"name": "phase:red"}]}
        ]

        # Execute
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        result = await tool.execute({"project_id": "project-test"})

        # Assert
        assert result.is_error is False
        validation_result = ValidationResult.model_validate_json(result.content[0]["text"])
        assert validation_result.valid is True  # Warnings only
        assert len(validation_result.warnings) >= 1
        warning_types = [w.type for w in validation_result.warnings]
        assert "issue_closed_early" in warning_types

    async def test_circular_dependency_detected(self, tmp_path: Path) -> None:
        """Test validation detects circular dependencies."""
        # Setup: Create .st3/projects.json with cycle
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True)
        
        metadata = ProjectMetadata(
            project_id="project-test",
            parent_issue={"number": 100, "url": "https://github.com/org/repo/issues/100"},
            milestone_id=10,
            phases={
                "A": SubIssueMetadata(
                    issue_number=101,
                    url="https://github.com/org/repo/issues/101",
                    depends_on=["C"],  # Cycle: A → C → B → A
                    blocks=["B"],
                    status="open"
                ),
                "B": SubIssueMetadata(
                    issue_number=102,
                    url="https://github.com/org/repo/issues/102",
                    depends_on=["A"],
                    blocks=["C"],
                    status="open"
                ),
                "C": SubIssueMetadata(
                    issue_number=103,
                    url="https://github.com/org/repo/issues/103",
                    depends_on=["B"],
                    blocks=["A"],
                    status="open"
                )
            }
        )
        
        projects_data = {"projects": {"project-test": metadata.model_dump()}}
        projects_file.write_text(json.dumps(projects_data))

        # Mock GitHub adapter
        mock_adapter = Mock()
        mock_adapter.get_milestone.return_value = {"number": 10, "state": "open"}
        mock_adapter.get_issue.side_effect = [
            {"number": 100, "state": "open", "labels": []},
            {"number": 101, "state": "open", "labels": [{"name": "phase:red"}]},
            {"number": 102, "state": "open", "labels": [{"name": "phase:red"}]},
            {"number": 103, "state": "open", "labels": [{"name": "phase:red"}]}
        ]

        # Execute
        tool = ValidateProjectStructureTool(
            github_adapter=mock_adapter,
            workspace_root=tmp_path
        )
        result = await tool.execute({"project_id": "project-test"})

        # Assert
        assert result.is_error is False
        validation_result = ValidationResult.model_validate_json(result.content[0]["text"])
        assert validation_result.valid is False
        assert len(validation_result.errors) == 1
        assert validation_result.errors[0].type == "circular_dependency"
        # Check message contains circular dependency indication
        message = validation_result.errors[0].message.lower()
        assert "circular" in message or "cycle" in message

    async def test_no_manager_configured(self) -> None:
        """Test tool returns error when manager not configured."""
        tool = ValidateProjectStructureTool()
        result = await tool.execute({"project_id": "test"})
        
        assert result.is_error is True
        assert "not configured" in result.content[0]["text"].lower()




