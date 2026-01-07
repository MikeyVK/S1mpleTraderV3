"""RED tests for PhaseStateEngine workflow validation.

Issue #50 - Step 3: PhaseStateEngine Integration

Tests workflow-based phase transition validation:
- Valid sequential transitions (allowed by workflow)
- Invalid transitions (rejected by workflow validation)
- Force transitions (bypass validation with skip_reason)
"""
from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


class TestPhaseStateEngineTransitions:
    """Test PhaseStateEngine with workflow validation."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return ProjectManager(workspace_root=workspace_root)

    @pytest.fixture
    def phase_engine(
        self, workspace_root: Path, project_manager: ProjectManager
    ) -> PhaseStateEngine:
        """Create PhaseStateEngine instance."""
        return PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

    def test_phase_state_engine_transition_valid(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        feature_phases: list[str]
    ) -> None:
        """Test valid sequential transition (phase[0] ÔåÆ phase[1])."""
        # Initialize project with feature workflow
        project_manager.initialize_project(
            issue_number=42,
            issue_title="Test feature",
            workflow_name="feature"
        )

        # Initialize branch state (current_phase = first phase)
        phase_engine.initialize_branch(
            branch="feature/42-test",
            issue_number=42,
            initial_phase=feature_phases[0]
        )

        # Valid transition: phase[0] ÔåÆ phase[1] (next phase in workflow)
        result = phase_engine.transition(
            branch="feature/42-test",
            to_phase=feature_phases[1],
            human_approval="Move to planning"
        )

        assert result["success"] is True
        assert result["from_phase"] == feature_phases[0]
        assert result["to_phase"] == feature_phases[1]

    def test_phase_state_engine_transition_invalid(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        feature_phases: list[str]
    ) -> None:
        """Test invalid transition (phase[0] ÔåÆ phase[2], skips phase[1])."""
        # Initialize project
        project_manager.initialize_project(
            issue_number=43,
            issue_title="Test feature",
            workflow_name="feature"
        )

        # Initialize branch state
        phase_engine.initialize_branch(
            branch="feature/43-test",
            issue_number=43,
            initial_phase=feature_phases[0]
        )

        # Invalid transition: phase[0] ÔåÆ phase[2] (skips phase[1])
        with pytest.raises(ValueError) as exc_info:
            phase_engine.transition(
                branch="feature/43-test",
                to_phase=feature_phases[2],
                human_approval="Skip planning"
            )

        error_msg = str(exc_info.value)
        assert "Invalid transition" in error_msg
        assert feature_phases[0] in error_msg
        assert feature_phases[2] in error_msg

    def test_phase_state_engine_force_transition(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        feature_phases: list[str]
    ) -> None:
        """Test force_transition allows non-sequential jumps."""
        # Initialize project
        project_manager.initialize_project(
            issue_number=44,
            issue_title="Test feature",
            workflow_name="feature"
        )

        # Initialize branch state
        phase_engine.initialize_branch(
            branch="feature/44-test",
            issue_number=44,
            initial_phase=feature_phases[0]
        )

        # Force transition: phase[0] ÔåÆ phase[2] (skip phase[1])
        result = phase_engine.force_transition(
            branch="feature/44-test",
            to_phase=feature_phases[2],
            skip_reason="Planning already done in previous project",
            human_approval="Force skip planning"
        )

        assert result["success"] is True
        assert result["from_phase"] == feature_phases[0]
        assert result["to_phase"] == feature_phases[2]
        assert result["forced"] is True
        assert result["skip_reason"] == "Planning already done in previous project"

    def test_phase_state_engine_get_current_phase(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        bug_phases: list[str]
    ) -> None:
        """Test get_current_phase returns correct phase."""
        # Initialize project and branch
        project_manager.initialize_project(
            issue_number=45,
            issue_title="Test",
            workflow_name="bug"
        )
        phase_engine.initialize_branch(
            branch="bug/45-test",
            issue_number=45,
            initial_phase=bug_phases[0]
        )

        # Get current phase
        current = phase_engine.get_current_phase(branch="bug/45-test")
        assert current == bug_phases[0]

    def test_phase_state_engine_get_workflow_name_from_cache(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        hotfix_phases: list[str]
    ) -> None:
        """Test workflow_name cached in state.json for performance."""
        # Initialize project and branch
        project_manager.initialize_project(
            issue_number=46,
            issue_title="Test",
            workflow_name="hotfix"
        )
        phase_engine.initialize_branch(
            branch="hotfix/46-test",
            issue_number=46,
            initial_phase=hotfix_phases[0]
        )

        # Get state (should include cached workflow_name)
        state = phase_engine.get_state(branch="hotfix/46-test")
        assert state["workflow_name"] == "hotfix"

    def test_phase_state_engine_transition_history_includes_forced_flag(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        feature_phases: list[str]
    ) -> None:
        """Test transition history marks forced transitions."""
        # Initialize project and branch
        project_manager.initialize_project(
            issue_number=47,
            issue_title="Test",
            workflow_name="feature"
        )
        phase_engine.initialize_branch(
            branch="feature/47-test",
            issue_number=47,
            initial_phase=feature_phases[0]
        )

        # Normal transition
        phase_engine.transition(
            branch="feature/47-test",
            to_phase=feature_phases[1],
            human_approval="Next phase"
        )

        # Forced transition
        phase_engine.force_transition(
            branch="feature/47-test",
            to_phase=feature_phases[3],
            skip_reason="Design already done",
            human_approval="Force skip design"
        )

        # Check transition history
        state = phase_engine.get_state(branch="feature/47-test")
        transitions = state["transitions"]

        # First transition (normal)
        assert transitions[0]["forced"] is False

        # Second transition (forced)
        assert transitions[1]["forced"] is True
        assert transitions[1]["skip_reason"] == "Design already done"

    def test_phase_state_engine_initialize_branch_without_project(
        self, phase_engine: PhaseStateEngine, feature_phases: list[str]
    ) -> None:
        """Test initialize_branch fails if project not initialized."""
        with pytest.raises(ValueError) as exc_info:
            phase_engine.initialize_branch(
                branch="feature/99-test",
                issue_number=99,
                initial_phase=feature_phases[0]
            )

        error_msg = str(exc_info.value)
        assert "Project 99 not found" in error_msg
        assert "Initialize project first" in error_msg

    def test_phase_state_engine_get_state_without_state_file(
        self, phase_engine: PhaseStateEngine
    ) -> None:
        """Test get_state fails if state.json doesn't exist."""
        with pytest.raises(ValueError) as exc_info:
            phase_engine.get_state(branch="feature/88-test")

        error_msg = str(exc_info.value)
        assert "Project plan not found" in error_msg

    def test_phase_state_engine_get_state_unknown_branch(
        self, phase_engine: PhaseStateEngine, project_manager: ProjectManager,
        feature_phases: list[str]
    ) -> None:
        """Test get_state fails for unknown branch."""
        # Initialize one branch to create state.json
        project_manager.initialize_project(
            issue_number=50,
            issue_title="Test",
            workflow_name="feature"
        )
        phase_engine.initialize_branch(
            branch="feature/50-test",
            issue_number=50,
            initial_phase=feature_phases[0]
        )

        # Try to get state for different branch
        with pytest.raises(ValueError) as exc_info:
            phase_engine.get_state(branch="feature/99-unknown")

        error_msg = str(exc_info.value)
        assert "Project plan not found" in error_msg
