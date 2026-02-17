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
    def engine(self, workspace_root: Path, project_manager: ProjectManager) -> PhaseStateEngine:
        """Create PhaseStateEngine instance.

        Args:
            workspace_root: Path to workspace root
            project_manager: ProjectManager instance

        Returns:
            PhaseStateEngine instance
        """
        return PhaseStateEngine(workspace_root=workspace_root, project_manager=project_manager)

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
            options=ProjectInitOptions(parent_branch="main"),
        )

        # Execute - initialize branch with different parent (override)
        result = engine.initialize_branch(
            branch="feature/79-test",
            issue_number=79,
            initial_phase="research",
            parent_branch="epic/76-qa",  # Override project's "main"
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
            options=ProjectInitOptions(parent_branch="epic/76-qa"),
        )

        # Execute - initialize branch WITHOUT parent_branch parameter
        result = engine.initialize_branch(
            branch="bug/80-test",
            issue_number=80,
            initial_phase="tdd",
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
            issue_number=81, issue_title="Old Project", workflow_name="docs"
        )

        # Execute - initialize branch
        result = engine.initialize_branch(
            branch="docs/81-test", issue_number=81, initial_phase="documentation"
        )

        # Verify
        assert result["success"] is True
        assert result["parent_branch"] is None

        # Verify persisted to state.json
        state = engine.get_state("docs/81-test")
        assert state["parent_branch"] is None

    def test_reconstruct_branch_state_includes_parent_branch(
        self, engine: PhaseStateEngine, project_manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test auto-recovery reconstructs parent_branch from projects.json.

        Issue #79: Cross-machine scenario - state.json missing after git pull.
        """
        # Setup - create project with parent_branch
        project_manager.initialize_project(
            issue_number=82,
            issue_title="Test Reconstruction",
            workflow_name="feature",
            options=ProjectInitOptions(parent_branch="epic/76-qa"),
        )

        # Simulate cross-machine: delete state.json but keep projects.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Execute - get_state triggers auto-recovery
        state = engine.get_state("feature/82-test-reconstruction")

        # Verify - parent_branch reconstructed from projects.json
        assert state["parent_branch"] == "epic/76-qa"
        assert state["reconstructed"] is True
        assert state["workflow_name"] == "feature"

    def test_reconstruct_branch_state_with_none_parent_branch(
        self, engine: PhaseStateEngine, project_manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test auto-recovery handles missing parent_branch gracefully.

        Issue #79: Old projects without parent_branch should reconstruct with None.
        """
        # Setup - create project WITHOUT parent_branch
        project_manager.initialize_project(
            issue_number=83, issue_title="Old Project", workflow_name="bug"
        )

        # Simulate cross-machine: delete state.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Execute - get_state triggers auto-recovery
        state = engine.get_state("bug/83-old-project")

        # Verify - parent_branch is None (backward compat)
        assert state["parent_branch"] is None
        assert state["reconstructed"] is True
        assert state["workflow_name"] == "bug"


class TestTddCycleTrackingFields:
    """Test TDD cycle tracking fields in state management.

    Issue #146: State management correctly initializes/clears cycle fields.
    """

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
    def engine(self, workspace_root: Path, project_manager: ProjectManager) -> PhaseStateEngine:
        """Create PhaseStateEngine instance.

        Args:
            workspace_root: Path to workspace root
            project_manager: ProjectManager instance

        Returns:
            PhaseStateEngine instance
        """
        return PhaseStateEngine(workspace_root=workspace_root, project_manager=project_manager)

    def test_initialize_branch_creates_tdd_cycle_fields(
        self, engine: PhaseStateEngine, project_manager: ProjectManager
    ) -> None:
        """Test initialize_branch creates tdd_cycle_* fields.

        Issue #146: current_tdd_cycle, last_tdd_cycle, tdd_cycle_history must be initialized.
        """
        # Setup - create project
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Execute - initialize branch
        result = engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking", issue_number=146, initial_phase="research"
        )

        # Verify - result contains success
        assert result["success"] is True

        # Verify - state.json contains tdd_cycle_* fields
        state = engine.get_state("feature/146-tdd-cycle-tracking")
        assert "current_tdd_cycle" in state
        assert "last_tdd_cycle" in state
        assert "tdd_cycle_history" in state

        # Verify - initial values
        assert state["current_tdd_cycle"] is None
        assert state["last_tdd_cycle"] is None
        assert state["tdd_cycle_history"] == []

    def test_reconstruct_state_includes_tdd_cycle_fields(
        self, engine: PhaseStateEngine, project_manager: ProjectManager, workspace_root: Path
    ) -> None:
        """Test auto-recovery includes tdd_cycle_* fields.

        Issue #146: Reconstructed state must include TDD cycle tracking fields.
        """
        # Setup - create project
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Simulate cross-machine: delete state.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Execute - get_state triggers auto-recovery
        state = engine.get_state("feature/146-tdd-cycle-tracking")

        # Verify - reconstructed flag
        assert state["reconstructed"] is True

        # Verify - tdd_cycle_* fields present
        assert "current_tdd_cycle" in state
        assert "last_tdd_cycle" in state
        assert "tdd_cycle_history" in state

        # Verify - initial values (None/[])
        assert state["current_tdd_cycle"] is None
        assert state["last_tdd_cycle"] is None
        assert state["tdd_cycle_history"] == []
