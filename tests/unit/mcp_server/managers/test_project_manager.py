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

from mcp_server.config.workflows import workflow_config
from mcp_server.managers import git_manager
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager


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
        expected = ["research", "planning", "design", "tdd", "integration", "documentation"]
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
            issue_number=42, issue_title="Add user authentication", workflow_name="feature"
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
            issue_number=99, issue_title="Critical security fix", workflow_name="hotfix"
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
            options=ProjectInitOptions(execution_mode="autonomous"),
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
        custom_phases = ("research", "planning", "design", "tdd", "integration", "documentation")

        result = manager.initialize_project(
            issue_number=50,
            issue_title="Complex refactor",
            workflow_name="refactor",
            options=ProjectInitOptions(
                custom_phases=custom_phases, skip_reason="Adding design phase for complex refactor"
            ),
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

    def test_initialize_project_invalid_workflow(self, manager: ProjectManager) -> None:
        """Test initialize_project rejects unknown workflow."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=999, issue_title="Test", workflow_name="invalid_workflow"
            )

        error_msg = str(exc_info.value)
        assert "Unknown workflow: 'invalid_workflow'" in error_msg
        assert "Available workflows:" in error_msg

    def test_initialize_project_invalid_execution_mode(self, manager: ProjectManager) -> None:
        """Test initialize_project rejects invalid execution_mode."""
        with pytest.raises(ValueError) as exc_info:
            manager.initialize_project(
                issue_number=888,
                issue_title="Test",
                workflow_name="feature",
                options=ProjectInitOptions(execution_mode="manual"),
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
                options=ProjectInitOptions(custom_phases=("research", "tdd")),
            )

        error_msg = str(exc_info.value)
        assert "skip_reason required when custom_phases provided" in error_msg

    def test_get_project_plan_returns_stored_plan(self, manager: ProjectManager) -> None:
        """Test get_project_plan retrieves stored project plan."""
        # Initialize project
        manager.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")

        # Retrieve plan
        plan = manager.get_project_plan(issue_number=42)
        assert plan is not None
        assert plan["workflow_name"] == "feature"
        assert plan["execution_mode"] == "interactive"
        assert len(plan["required_phases"]) == 6

    def test_get_project_plan_nonexistent_returns_none(self, manager: ProjectManager) -> None:
        """Test get_project_plan returns None for nonexistent project."""
        plan = manager.get_project_plan(issue_number=999)
        assert plan is None

    def test_initialize_project_with_parent_branch(self, manager: ProjectManager) -> None:
        """Test initializing project with explicit parent_branch.

        Issue #79: parent_branch tracking for merge targets.
        """
        result = manager.initialize_project(
            issue_number=79,
            issue_title="Add parent branch tracking",
            workflow_name="feature",
            options=ProjectInitOptions(parent_branch="epic/76-quality-gates-tooling"),
        )

        # Verify parent_branch in returned result
        assert result["parent_branch"] == "epic/76-quality-gates-tooling"

        # Verify persisted to projects.json
        plan = manager.get_project_plan(issue_number=79)
        assert plan is not None
        assert plan["parent_branch"] == "epic/76-quality-gates-tooling"

    def test_initialize_project_without_parent_branch(self, manager: ProjectManager) -> None:
        """Test initializing project without parent_branch (backward compat).

        Issue #79: parent_branch is optional for existing workflows.
        """
        result = manager.initialize_project(
            issue_number=80, issue_title="Old style project", workflow_name="bug"
        )

        # Verify parent_branch is None
        assert result["parent_branch"] is None

        # Verify persisted as None
        plan = manager.get_project_plan(issue_number=80)
        assert plan is not None
        assert plan["parent_branch"] is None


class TestProjectManagerPhaseDetection:
    """Test ProjectManager phase detection (Issue #139).

    Cycle 3.2: get_project_plan should return current_phase via ScopeDecoder.
    """

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace with .st3 directory."""
        st3_dir = tmp_path / ".st3"
        st3_dir.mkdir()

        # Create workphases.yaml
        workphases_path = st3_dir / "workphases.yaml"
        workphases_path.write_text(
            """
version: "1.0"
phases:
  research:
    display_name: "Research"
    commit_type_hint: "docs"
    subphases: []
  tdd:
    display_name: "TDD"
    commit_type_hint: null
    subphases: ["red", "green", "refactor"]
  documentation:
    display_name: "Documentation"
    commit_type_hint: "docs"
    subphases: ["reference", "guides"]
"""
        )

        return tmp_path

    @pytest.fixture
    def manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return ProjectManager(workspace_root=workspace_root)

    def test_get_project_plan_includes_current_phase_from_commit_scope(
        self, manager: ProjectManager
    ) -> None:
        """Test get_project_plan returns current_phase from commit-scope.

        Issue #139: Phase detection via ScopeDecoder (commit-scope > state.json > unknown).
        """
        # Initialize project
        manager.initialize_project(
            issue_number=139,
            issue_title="Add current_phase to get_project_plan",
            workflow_name="feature",
        )

        # Mock a commit with scope
        # Note: This test will fail (RED) until we integrate GitManager
        plan = manager.get_project_plan(issue_number=139)

        # Assertions for Issue #139 fix
        assert plan is not None
        assert "current_phase" in plan
        assert "phase_source" in plan
        assert "phase_detection_error" in plan

    def test_get_project_plan_returns_unknown_when_no_commits(
        self, manager: ProjectManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_project_plan returns unknown phase when no commits exist."""
        # Mock GitManager.get_recent_commits to return empty list
        monkeypatch.setattr(
            git_manager.GitManager, "get_recent_commits", lambda _self, _limit=10: []
        )

        # Initialize project
        manager.initialize_project(
            issue_number=140,
            issue_title="Test unknown phase",
            workflow_name="bug",
        )

        plan = manager.get_project_plan(issue_number=140)

        # Should return unknown with error message
        assert plan is not None
        assert plan["current_phase"] == "unknown"
        assert plan["phase_source"] == "unknown"
        assert plan["phase_detection_error"] is not None


class TestPlanningDeliverablesSchema:
    """Test planning_deliverables schema storage (Issue #146 Cycle 1)."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return ProjectManager(workspace_root=workspace_root)

    def test_planning_deliverables_stored_in_projects_json(self, manager: ProjectManager) -> None:
        """Test that planning_deliverables are persisted to projects.json.

        RED: This test WILL FAIL - planning_deliverables schema not implemented yet.
        """
        # Arrange: Create planning deliverables according to design.md schema
        planning_deliverables = {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle": 1,
                        "name": "Schema & Storage",
                        "deliverables": ["planning_deliverables schema", "tdd_cycle_* fields"],
                        "exit_criteria": "Schema validated, tests pass",
                    }
                ],
            }
        }

        # Act: Initialize project and save planning deliverables
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Save planning deliverables (method doesn't exist yet - will fail)
        manager.save_planning_deliverables(146, planning_deliverables)

        # Assert: Retrieve and verify planning deliverables persisted
        plan = manager.get_project_plan(146)
        assert plan is not None
        assert "planning_deliverables" in plan
        assert plan["planning_deliverables"]["tdd_cycles"]["total"] == 4
        assert len(plan["planning_deliverables"]["tdd_cycles"]["cycles"]) == 1

    def test_save_planning_deliverables_rejects_duplicate(self, manager: ProjectManager) -> None:
        """Test that save_planning_deliverables rejects duplicate saves."""
        # Arrange
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )
        planning_deliverables = {"tdd_cycles": {"total": 4, "cycles": []}}
        manager.save_planning_deliverables(146, planning_deliverables)

        # Act & Assert: Second save should fail
        with pytest.raises(ValueError, match="already exist"):
            manager.save_planning_deliverables(146, planning_deliverables)

    def test_save_planning_deliverables_rejects_missing_tdd_cycles(
        self, manager: ProjectManager
    ) -> None:
        """Test schema validation: tdd_cycles required."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Missing tdd_cycles key
        with pytest.raises(ValueError, match="must contain 'tdd_cycles' key"):
            manager.save_planning_deliverables(146, {"validation_plan": {}})

    def test_save_planning_deliverables_rejects_malformed_tdd_cycles(
        self, manager: ProjectManager
    ) -> None:
        """Test schema validation: tdd_cycles structure."""
        manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # tdd_cycles not a dict
        with pytest.raises(ValueError, match="must be a dict"):
            manager.save_planning_deliverables(146, {"tdd_cycles": "invalid"})

        # Missing total key
        with pytest.raises(ValueError, match="must contain 'total' key"):
            manager.save_planning_deliverables(146, {"tdd_cycles": {"cycles": []}})

        # Invalid total (not int)
        with pytest.raises(ValueError, match="must be a positive integer"):
            manager.save_planning_deliverables(146, {"tdd_cycles": {"total": "4", "cycles": []}})

        # Invalid total (zero)
        with pytest.raises(ValueError, match="must be a positive integer"):
            manager.save_planning_deliverables(146, {"tdd_cycles": {"total": 0, "cycles": []}})

        # Missing cycles key
        with pytest.raises(ValueError, match="must contain 'cycles' key"):
            manager.save_planning_deliverables(146, {"tdd_cycles": {"total": 4}})

        # Invalid cycles (not list)
        with pytest.raises(ValueError, match="must be a list"):
            manager.save_planning_deliverables(
                146, {"tdd_cycles": {"total": 4, "cycles": "invalid"}}
            )
