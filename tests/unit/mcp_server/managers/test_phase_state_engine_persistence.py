"""Tests for PhaseStateEngine state.json persistence.

Issue #85: Single-branch state model - state.json should contain ONLY current branch.

Tests verify:
1. state.json contains single branch state (not multi-branch dictionary)
2. Branch switch overwrites state.json completely
3. State is immediately written and readable after get_state()
"""
import json
from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


class TestPhaseStateEnginePersistence:
    """Test state.json persistence and single-branch model."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager with two test projects."""
        manager = ProjectManager(workspace_root=workspace_root)
        # Create project 1
        manager.initialize_project(
            issue_number=1,
            issue_title="First feature",
            workflow_name="feature"
        )
        # Create project 2
        manager.initialize_project(
            issue_number=2,
            issue_title="Second feature",
            workflow_name="feature"
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

    def test_state_json_contains_single_branch_only(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that state.json contains ONLY the current branch state.

        GIVEN: Two branches exist (feature/1-first, feature/2-second)
        WHEN: get_state() is called for feature/1-first
        THEN: state.json should contain ONLY feature/1-first state (top-level dict)
        AND: state.json should NOT contain nested branch dictionaries
        """
        # Get state for first branch
        state_engine.get_state("feature/1-first-feature")

        # Read state.json directly from disk
        state_file = workspace_root / ".st3" / "state.json"
        assert state_file.exists(), "state.json should be created"

        with open(state_file, encoding='utf-8') as f:
            disk_state = json.load(f)

        # Verify single-branch model: top-level dict should BE the branch state
        assert disk_state.get("branch") == "feature/1-first-feature", \
            "state.json should contain the current branch at top level"
        assert disk_state.get("issue_number") == 1, \
            "state.json should contain branch fields at top level"

        # Verify no nested branch dictionaries
        assert "feature/1-first-feature" not in disk_state, \
            "state.json should NOT contain branch name as nested key"
        assert "feature/2-second-feature" not in disk_state, \
            "state.json should NOT contain other branches"

    def test_branch_switch_overwrites_state_json_completely(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that switching branches completely overwrites state.json.

        GIVEN: state.json contains feature/1-first state
        WHEN: get_state() is called for feature/2-second
        THEN: state.json should be completely replaced with feature/2-second state
        AND: No trace of feature/1-first should remain
        """
        # Set up: Get state for first branch
        state_engine.get_state("feature/1-first-feature")

        # Switch to second branch
        state_engine.get_state("feature/2-second-feature")

        # Read state.json
        state_file = workspace_root / ".st3" / "state.json"
        with open(state_file, encoding='utf-8') as f:
            disk_state = json.load(f)

        # Verify complete overwrite
        assert disk_state.get("branch") == "feature/2-second-feature", \
            "state.json should contain new branch"
        assert disk_state.get("issue_number") == 2, \
            "state.json should contain new issue number"

        # Verify old branch is gone
        assert disk_state.get("issue_number") != 1, \
            "Old branch data should be completely removed"
        assert "feature/1-first-feature" not in json.dumps(disk_state), \
            "No reference to old branch should exist"

    def test_state_immediately_readable_after_get_state(
        self, state_engine: PhaseStateEngine, workspace_root: Path
    ) -> None:
        """Test that state.json is immediately readable after get_state().

        GIVEN: No state.json exists
        WHEN: get_state() is called
        THEN: state.json should be immediately readable from disk
        AND: Content should match the returned state
        """
        # Get state
        returned_state = state_engine.get_state("feature/1-first-feature")

        # Immediately read from disk (no delay, no flush needed)
        state_file = workspace_root / ".st3" / "state.json"
        assert state_file.exists(), "state.json should exist immediately"

        with open(state_file, encoding='utf-8') as f:
            disk_state = json.load(f)

        # Verify content matches
        assert disk_state == returned_state, \
            "Disk state should match returned state immediately"
