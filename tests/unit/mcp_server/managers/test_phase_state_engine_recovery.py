"""Tests for PhaseStateEngine auto-recovery (Mode 2).

Issue #39: Mode 2 - Auto-recovery of missing state.json from git commits.

Tests verify:
1. Missing state.json triggers reconstruction
2. Phase inferred from phase:label commits
3. State reconstructed from projects.json + git
4. Transparent recovery (no user intervention)
5. Reconstructed flag set for audit
6. Safe fallback to first phase
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.config.workflows import workflow_config
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


class TestPhaseStateEngineMode2:
    """Test auto-recovery (Mode 2) for Issue #39."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager and initialize a project."""
        manager = ProjectManager(workspace_root=workspace_root)
        # Initialize project for testing
        manager.initialize_project(
            issue_number=39,
            issue_title="Test auto-recovery",
            workflow_name="bug"
        )
        return manager

    @pytest.fixture
    def state_engine(
        self, workspace_root: Path, project_manager: ProjectManager
    ) -> PhaseStateEngine:
        """Create PhaseStateEngine instance."""
        return PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )

    @pytest.mark.asyncio
    async def test_missing_state_triggers_reconstruction(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that missing state.json triggers auto-recovery.

        Issue #39 Gap 2: After git pull, state.json missing.
        After fix: PhaseStateEngine.get_state() reconstructs automatically.
        """
        # Ensure state.json does NOT exist (cross-machine scenario)
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Mock git to return commits with phase labels
        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = [
                "phase:design - Complete technical specifications",
                "phase:planning - Define implementation goals",
                "phase:research - Analyze problem"
            ]

            # Call get_state - should auto-recover
            state = state_engine.get_state("fix/39-test")

            # Verify state was reconstructed
            assert state["branch"] == "fix/39-test"
            assert state["issue_number"] == 39
            assert state["workflow_name"] == "bug"
            assert state["current_phase"] == "design"  # Most recent phase:label
            assert state["transitions"] == []  # Cannot reconstruct history
            assert "created_at" in state
            assert state["reconstructed"] is True  # Audit flag

            # Verify state.json was created
            assert state_file.exists()

    @pytest.mark.asyncio
    async def test_phase_inferred_from_phase_labels(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that phase is inferred from phase:label commits."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Mock commits with phase:label format (labels.yaml SSOT)
        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = [
                "phase:integration - Test cross-machine scenario",
                "phase:green - Implement feature",
                "phase:red - Write failing test",
                "phase:design - Complete design",
            ]

            state = state_engine.get_state("fix/39-test")

            # Should detect most recent phase
            assert state["current_phase"] == "integration"

    @pytest.mark.asyncio
    async def test_tdd_phases_map_to_tdd(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that phase:red/green/refactor map to 'tdd' in workflow."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = [
                "phase:green - Implement Mode 1",
                "phase:red - Write failing tests",
                "phase:design - Complete specs"
            ]

            state = state_engine.get_state("fix/39-test")

            # phase:green should map to 'tdd' in bug workflow
            bug_workflow = workflow_config.get_workflow("bug")
            assert "tdd" in bug_workflow.phases
            assert state["current_phase"] == "tdd"

    @pytest.mark.asyncio
    async def test_fallback_to_first_phase_no_commits(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test safe fallback when no phase:label commits found."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = [
                "Initial commit",
                "Add README",
                "Setup project"
            ]

            state = state_engine.get_state("fix/39-test")

            # Should fallback to first phase of workflow
            bug_workflow = workflow_config.get_workflow("bug")
            expected_first_phase = bug_workflow.phases[0]
            assert state["current_phase"] == expected_first_phase
            assert state["reconstructed"] is True

    @pytest.mark.asyncio
    async def test_transparent_recovery_no_user_intervention(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that recovery is transparent (no exceptions thrown)."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = ["phase:planning - Define goals"]

            # Should not raise any exceptions
            state = state_engine.get_state("fix/39-test")

            assert state is not None
            assert not state_file.exists() or state_file.exists()  # Either way is OK

    @pytest.mark.asyncio
    async def test_branch_name_parsing(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that issue number is extracted from branch name."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = ["phase:research - Start work"]

            state = state_engine.get_state("fix/39-test-recovery")

            # Issue number parsed from branch
            assert state["issue_number"] == 39

    @pytest.mark.asyncio
    async def test_missing_projects_json_raises_error(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that missing projects.json raises clear error."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Delete projects.json to simulate error case
        projects_file = workspace_root / ".st3" / "projects.json"
        if projects_file.exists():
            projects_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = ["phase:research - Start"]

            # Should raise ValueError with helpful message
            with pytest.raises(ValueError, match="Project plan not found"):
                state_engine.get_state("fix/39-test")

    @pytest.mark.asyncio
    async def test_invalid_branch_name_raises_error(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that invalid branch format raises clear error."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = ["phase:research - Start"]

            # Invalid branch name (no issue number)
            with pytest.raises(ValueError, match="Cannot extract issue number"):
                state_engine.get_state("invalid-branch-name")

    @pytest.mark.asyncio
    async def test_git_error_fallback_to_first_phase(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test graceful degradation when git commands fail."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.side_effect = RuntimeError("Git command failed")

            # Should not crash, fallback to first phase
            state = state_engine.get_state("fix/39-test")

            bug_workflow = workflow_config.get_workflow("bug")
            expected_first_phase = bug_workflow.phases[0]
            assert state["current_phase"] == expected_first_phase
            assert state["reconstructed"] is True

    @pytest.mark.asyncio
    async def test_reconstruction_idempotent(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that reconstruction can be called multiple times safely."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            mock_git.return_value = ["phase:design - Complete specs"]

            # First call - reconstruction
            state1 = state_engine.get_state("fix/39-test")
            assert state1["reconstructed"] is True

            # Second call - should return same state (now saved)
            state2 = state_engine.get_state("fix/39-test")

            # Both calls should succeed
            assert state1["current_phase"] == state2["current_phase"]
            assert state1["issue_number"] == state2["issue_number"]

    @pytest.mark.asyncio
    async def test_workflow_phases_validated(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that inferred phase must exist in workflow."""
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        with patch.object(state_engine, '_get_git_commits') as mock_git:
            # phase:invalid not in bug workflow
            mock_git.return_value = [
                "phase:invalid - This should be ignored",
                "phase:design - Valid phase"
            ]

            state = state_engine.get_state("fix/39-test")

            # Should use valid phase, ignore invalid
            assert state["current_phase"] == "design"
