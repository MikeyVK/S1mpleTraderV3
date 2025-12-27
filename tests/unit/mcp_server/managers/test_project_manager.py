"""Tests for ProjectManager with workflow-based initialization.

Issue #50: Tests migrated from PHASE_TEMPLATES to workflows.yaml.
- Workflow selection from workflows.yaml
- Execution mode handling (interactive/autonomous)
- Custom phases with skip_reason
- Project plan storage in .st3/projects.json
"""
import json
from pathlib import Path

import pytest

from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager
from mcp_server.config.workflows import workflow_config


class TestProjectManagerWorkflows:
    """Test ProjectManager with workflows.yaml integration."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace.

        Args:
            tmp_path: Pytest tmp_path fixture

        Returns:
            Path to temporary workspace root
        """
        return tmp_path

    @pytest.fixture
    def manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance.

        Args:
            workspace_root: Path to workspace root

        Returns:
            ProjectManager instance
        """
        return ProjectManager(workspace_root=workspace_root)

    def test_workflows_loaded_from_yaml(self) -> None:
        """Test that workflows are loaded from workflows.yaml."""
        assert "feature" in workflow_config.workflows
        assert "bug" in workflow_config.workflows
        assert "hotfix" in workflow_config.workflows
        assert "refactor" in workflow_config.workflows
        assert "docs" in workflow_config.workflows

    def test_feature_workflow_has_6_phases(self) -> None:
        """Test feature workflow from workflows.yaml."""
        workflow = workflow_config.get_workflow("feature")
        assert len(workflow.phases) == 6
        expected = ["discovery", "planning", "design", "tdd", "integration", "documentation"]
        assert workflow.phases == expected
        assert workflow.default_execution_mode == "interactive"

    def test_hotfix_workflow_has_3_phases_autonomous(self) -> None:
        """Test hotfix workflow from workflows.yaml."""
        workflow = workflow_config.get_workflow("hotfix")
        assert len(workflow.phases) == 3
        assert workflow.phases == ["tdd", "integration", "documentation"]
        assert workflow.default_execution_mode == "autonomous"

    def test_initialize_project_with_feature_workflow(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with feature workflow."""
        result = manager.initialize_project(
            issue_number=42,
            issue_title="Add user authentication",
            workflow_name="feature"
        )

        assert result["success"] is True
        assert result["workflow_name"] == "feature"
        assert result["execution_mode"] == "interactive"
        assert len(result["required_phases"]) == 6

        # Check projects.json structure
        projects_file = workspace_root / ".st3" / "projects.json"
        assert projects_file.exists()

        projects = json.loads(projects_file.read_text())
        assert "42" in projects
        project = projects["42"]
        assert project["workflow_name"] == "feature"
        assert project["execution_mode"] == "interactive"
        assert len(project["required_phases"]) == 6

    def test_initialize_project_with_hotfix_workflow(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with hotfix workflow (autonomous)."""
        result = manager.initialize_project(
            issue_number=99,
            issue_title="Critical security fix",
            workflow_name="hotfix"
        )

        assert result["success"] is True
        assert result["workflow_name"] == "hotfix"
        assert result["execution_mode"] == "autonomous"
        assert len(result["required_phases"]) == 3

        # Check projects.json
        projects_file = workspace_root / ".st3" / "projects.json"
        projects = json.loads(projects_file.read_text())
        assert projects["99"]["execution_mode"] == "autonomous"

    def test_initialize_project_with_execution_mode_override(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test execution_mode override (feature normally interactive)."""
        result = manager.initialize_project(
            issue_number=77,
            issue_title="Test",
            workflow_name="feature",
            options=ProjectInitOptions(execution_mode="autonomous")
        )

        assert result["execution_mode"] == "autonomous"

        # Check projects.json
        projects_file = workspace_root / ".st3" / "projects.json"
        projects = json.loads(projects_file.read_text())
        assert projects["77"]["execution_mode"] == "autonomous"

    def test_initialize_project_with_custom_phases(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with custom phases."""
        custom_phases = ("discovery", "planning", "design", "tdd", "integration", "documentation")

        result = manager.initialize_project(
            issue_number=50,
            issue_title="Complex refactor",
            workflow_name="refactor",
            options=ProjectInitOptions(
                custom_phases=custom_phases,
                skip_reason="Adding design phase for complex refactor"
            )
        )

        assert result["success"] is True
        assert result["workflow_name"] == "refactor"
        assert result["required_phases"] == custom_phases
        assert result["skip_reason"] == "Adding design phase for complex refactor"

        # Check projects.json
        projects_file = workspace_root / ".st3" / "projects.json"
        projects = json.loads(projects_file.read_text())
        project = projects["50"]
        assert tuple(project["required_phases"]) == custom_phases
        assert project["skip_reason"] == "Adding design phase for complex refactor"

    def test_initialize_project_invalid_workflow(
        self, manager: ProjectManager
    ) -> None:
        """Test initialize_project rejects unknown workflow."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=999,
                issue_title="Test",
                workflow_name="invalid_workflow"
            )

        error_msg = str(exc_info.value)
        assert "Unknown workflow: 'invalid_workflow'" in error_msg
        assert "Available workflows:" in error_msg

    def test_initialize_project_invalid_execution_mode(
        self, manager: ProjectManager
    ) -> None:
        """Test initialize_project rejects invalid execution_mode."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=888,
                issue_title="Test",
                workflow_name="feature",
                options=ProjectInitOptions(execution_mode="manual")
            )

        error_msg = str(exc_info.value)
        assert "Invalid execution_mode: 'manual'" in error_msg
        assert "Valid values: 'interactive', 'autonomous'" in error_msg

    def test_initialize_project_custom_phases_without_skip_reason(
        self, manager: ProjectManager
    ) -> None:
        """Test initialize_project requires skip_reason with custom_phases."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=777,
                issue_title="Test",
                workflow_name="feature",
                options=ProjectInitOptions(custom_phases=("discovery", "tdd"))
            )

        error_msg = str(exc_info.value)
        assert "skip_reason required when custom_phases provided" in error_msg

    def test_get_project_plan_returns_stored_plan(
        self, manager: ProjectManager
    ) -> None:
        """Test get_project_plan retrieves stored project plan."""
        # Initialize project
        manager.initialize_project(
            issue_number=42,
            issue_title="Test",
            workflow_name="feature"
        )

        # Retrieve plan
        plan = manager.get_project_plan(issue_number=42)
        assert plan is not None
        assert plan["workflow_name"] == "feature"
        assert plan["execution_mode"] == "interactive"
        assert len(plan["required_phases"]) == 6

    def test_get_project_plan_nonexistent_returns_none(
        self, manager: ProjectManager
    ) -> None:
        """Test get_project_plan returns None for nonexistent project."""
        plan = manager.get_project_plan(issue_number=999)
        assert plan is None
