"""Tests for ProjectManager workflow integration (Issue #50).

Tests the migration from issue_type + PHASE_TEMPLATES to workflow_name + workflows.yaml.

Test Coverage:
- initialize_project with workflow_name parameter
- Workflow validation against workflows.yaml
- projects.json structure with workflow_name and execution_mode
- Custom phases with skip_reason

Quality Requirements:
- Pylint: 10/10 (strict enforcement)
- Mypy: strict mode passing
- Coverage: 100% for new workflow integration code
"""
import json
from pathlib import Path

import pytest

from mcp_server.managers.project_manager import ProjectManager
from mcp_server.config.workflows import workflow_config


class TestProjectManagerWorkflowIntegration:
    """Test ProjectManager integration with workflows.yaml."""

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

    def test_initialize_project_with_workflow_name(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project accepts workflow_name parameter.

        Expected behavior:
        - Accepts workflow_name instead of issue_type
        - Looks up workflow from workflow_config
        - Stores workflow_name in projects.json
        - Stores execution_mode from workflow default

        Args:
            manager: ProjectManager instance
            workspace_root: Path to workspace root
        """
        result = manager.initialize_project(
            issue_number=50,
            issue_title="Test workflow integration",
            workflow_name="feature"  # type: ignore[call-arg]
        )

        assert result["success"] is True
        assert result["workflow_name"] == "feature"
        assert result["execution_mode"] == "interactive"  # feature default
        assert len(result["required_phases"]) == 6  # feature has 6 phases in workflows.yaml

        # Check projects.json structure
        projects_file = workspace_root / ".st3" / "projects.json"
        assert projects_file.exists()

        projects = json.loads(projects_file.read_text())
        assert "50" in projects
        project = projects["50"]
        assert project["workflow_name"] == "feature"
        assert project["execution_mode"] == "interactive"
        assert "issue_type" not in project  # OLD field removed

    def test_initialize_project_with_unknown_workflow(
        self, manager: ProjectManager
    ) -> None:
        """Test initialize_project rejects unknown workflow_name.

        Expected behavior:
        - Raises ValueError for unknown workflow
        - Error message lists available workflows

        Args:
            manager: ProjectManager instance
        """
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=99,
                issue_title="Test unknown workflow",
                workflow_name="nonexistent"  # type: ignore[call-arg]
            )

        error_msg = str(exc_info.value)
        assert "Unknown workflow: 'nonexistent'" in error_msg
        assert "Available workflows:" in error_msg

    def test_initialize_project_with_hotfix_workflow(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with hotfix workflow (autonomous mode).

        Expected behavior:
        - Uses hotfix workflow (3 phases)
        - Sets execution_mode to autonomous (hotfix default)

        Args:
            manager: ProjectManager instance
            workspace_root: Path to workspace root
        """
        result = manager.initialize_project(
            issue_number=100,
            issue_title="Critical bug fix",
            workflow_name="hotfix"  # type: ignore[call-arg]
        )

        assert result["workflow_name"] == "hotfix"
        assert result["execution_mode"] == "autonomous"  # hotfix default
        assert len(result["required_phases"]) == 3

        # Check projects.json
        projects_file = workspace_root / ".st3" / "projects.json"
        projects = json.loads(projects_file.read_text())
        assert projects["100"]["execution_mode"] == "autonomous"

    def test_initialize_project_with_custom_phases_and_workflow(
        self, manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test initialize_project with custom phases overriding workflow.

        Expected behavior:
        - Accepts both workflow_name and custom_phases
        - custom_phases overrides workflow phases
        - Requires skip_reason for custom phases
        - Stores custom phases in projects.json

        Args:
            manager: ProjectManager instance
            workspace_root: Path to workspace root
        """
        custom_phases = ("discovery", "planning", "design", "tdd", "integration", "documentation")

        result = manager.initialize_project(
            issue_number=50,
            issue_title="Refactor with design phase",
            workflow_name="refactor",  # type: ignore[call-arg]
            custom_phases=custom_phases,
            skip_reason="Adding design phase for complex refactor"
        )

        assert result["workflow_name"] == "refactor"
        assert result["required_phases"] == custom_phases
        assert result["skip_reason"] == "Adding design phase for complex refactor"

        # Check projects.json
        projects_file = workspace_root / ".st3" / "projects.json"
        projects = json.loads(projects_file.read_text())
        project = projects["50"]
        assert project["workflow_name"] == "refactor"
        assert tuple(project["required_phases"]) == custom_phases
        assert project["skip_reason"] == "Adding design phase for complex refactor"

    def test_initialize_project_workflow_phases_correct(
        self, manager: ProjectManager
    ) -> None:
        """Test that workflow phases match workflows.yaml definitions.

        Expected behavior:
        - feature: 6 phases (discovery, planning, design, tdd, integration, documentation)
        - bug: 5 phases (discovery, planning, tdd, integration, documentation)
        - hotfix: 3 phases (tdd, integration, documentation)
        - refactor: 5 phases (discovery, planning, tdd, integration, documentation)
        - docs: 2 phases (planning, documentation)

        Args:
            manager: ProjectManager instance
        """
        # Get actual workflow phases from workflow_config
        feature_phases = workflow_config.get_workflow("feature").phases
        bug_phases = workflow_config.get_workflow("bug").phases
        hotfix_phases = workflow_config.get_workflow("hotfix").phases
        refactor_phases = workflow_config.get_workflow("refactor").phases
        docs_phases = workflow_config.get_workflow("docs").phases

        # Test feature
        result = manager.initialize_project(
            1, "Test", workflow_name="feature"  # type: ignore[call-arg]
        )
        assert tuple(result["required_phases"]) == tuple(feature_phases)

        # Test bug
        result = manager.initialize_project(
            2, "Test", workflow_name="bug"  # type: ignore[call-arg]
        )
        assert tuple(result["required_phases"]) == tuple(bug_phases)

        # Test hotfix
        result = manager.initialize_project(
            3, "Test", workflow_name="hotfix"  # type: ignore[call-arg]
        )
        assert tuple(result["required_phases"]) == tuple(hotfix_phases)

        # Test refactor
        result = manager.initialize_project(
            4, "Test", workflow_name="refactor"  # type: ignore[call-arg]
        )
        assert tuple(result["required_phases"]) == tuple(refactor_phases)

        # Test docs
        result = manager.initialize_project(
            5, "Test", workflow_name="docs"  # type: ignore[call-arg]
        )
        assert tuple(result["required_phases"]) == tuple(docs_phases)
