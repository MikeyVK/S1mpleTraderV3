"""Tests for PhaseStateEngine with parent_branch tracking.

Issue #79: Tests for parent_branch in state management.
- initialize_branch with parent_branch
- Auto-recovery includes parent_branch from projects.json
"""
from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager


class TestPhaseStateEngineParentBranch:
    """Test parent_branch functionality in PhaseStateEngine."""

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
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance.

        Args:
            workspace_root: Path to workspace root

        Returns:
            ProjectManager instance
        """
        return ProjectManager(workspace_root=workspace_root)

    @pytest.fixture
    def engine(
        self, workspace_root: Path, project_manager: ProjectManager
    ) -> PhaseStateEngine:
        """Create PhaseStateEngine instance.

        Args:
            workspace_root: Path to workspace root
            project_manager: ProjectManager instance

        Returns:
            PhaseStateEngine instance
        """
        return PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

    def test_initialize_branch_with_explicit_parent_branch(
        self, engine: PhaseStateEngine, project_manager: ProjectManager
    ) -> None:
        """Test initializing branch with explicit parent_branch.

        Issue #79: parent_branch can be passed explicitly to override project's value.
        """
        # Setup - create project with one parent
        project_manager.initialize_project(
            issue_number=79,
            issue_title="Test",
            workflow_name="feature",
            options=ProjectInitOptions(parent_branch="main")
        )

        # Execute - initialize branch with different parent (override)
        result = engine.initialize_branch(
            branch="feature/79-test",
            issue_number=79,
            initial_phase="research",
            parent_branch="epic/76-qa"  # Override project's "main"
        )

        # Verify
        assert result["success"] is True
        assert result["parent_branch"] == "epic/76-qa"

        # Verify persisted to state.json
        state = engine.get_state("feature/79-test")
        assert state["parent_branch"] == "epic/76-qa"

    def test_initialize_branch_inherits_parent_from_project(
        self, engine: PhaseStateEngine, project_manager: ProjectManager
    ) -> None:
        """Test initializing branch inherits parent_branch from project.

        Issue #79: If parent_branch not provided, inherit from projects.json.
        """
        # Setup - create project with parent
        project_manager.initialize_project(
            issue_number=80,
            issue_title="Test",
            workflow_name="bug",
            options=ProjectInitOptions(parent_branch="epic/76-qa")
        )

        # Execute - initialize branch WITHOUT parent_branch parameter
        result = engine.initialize_branch(
            branch="bug/80-test",
            issue_number=80,
            initial_phase="tdd"
            # No parent_branch - should inherit from project
        )

        # Verify
        assert result["success"] is True
        assert result["parent_branch"] == "epic/76-qa"

        # Verify persisted to state.json
        state = engine.get_state("bug/80-test")
        assert state["parent_branch"] == "epic/76-qa"

    def test_initialize_branch_with_none_parent_branch(
        self, engine: PhaseStateEngine, project_manager: ProjectManager
    ) -> None:
        """Test initializing branch when project has no parent_branch.

        Issue #79: Backward compatibility - parent_branch can be None.
        """
        # Setup - create project WITHOUT parent_branch
        project_manager.initialize_project(
            issue_number=81,
            issue_title="Old Project",
            workflow_name="docs"
        )

        # Execute - initialize branch
        result = engine.initialize_branch(
            branch="docs/81-test",
            issue_number=81,
            initial_phase="documentation"
        )

        # Verify
        assert result["success"] is True
        assert result["parent_branch"] is None

        # Verify persisted to state.json
        state = engine.get_state("docs/81-test")
        assert state["parent_branch"] is None
