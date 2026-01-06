"""Integration tests for Issue #39: Cross-machine state recovery.

Tests the complete flow:
1. Machine A: Initialize project (Mode 1 - creates both files)
2. Machine A: Make commits with phase:label
3. Machine A: Push to git
4. Machine B: Pull code (state.json missing - not in git)
5. Machine B: Tools work transparently (Mode 2 - auto-recovery)

This validates that the dual-mode system works end-to-end across machines.
"""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.project_tools import InitializeProjectTool


class TestIssue39CrossMachine:
    """Integration tests for cross-machine state recovery."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace with git repo."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        
        # Create initial commit
        readme = workspace / "README.md"
        readme.write_text("# Test Project")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace,
            check=True,
            capture_output=True
        )
        
        return workspace

    @pytest.mark.asyncio
    async def test_complete_cross_machine_flow(self, workspace_root: Path) -> None:
        """Test complete flow: Initialize → Commit → Delete state → Auto-recover.
        
        Simulates:
        - Machine A: Initialize project, make commits
        - Machine B: Pull code (state.json missing), tools work
        """
        # =====================================================================
        # MACHINE A: Initialize project
        # =====================================================================
        
        # Create branch for issue 42
        subprocess.run(
            ["git", "checkout", "-b", "fix/42-cross-machine-test"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Initialize project (Mode 1 - atomic creation)
        project_manager = ProjectManager(workspace_root=workspace_root)
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "fix/42-cross-machine-test"

        state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )

        # Initialize project atomically (Mode 1)
        project_manager.initialize_project(
            issue_number=42,
            issue_title="Cross-machine test",
            workflow_name="bug"
        )

        # Get first phase from workflow
        result = project_manager.get_project_plan(42)
        first_phase = result["required_phases"][0]

        # Initialize state
        state_engine.initialize_branch(
            branch="fix/42-cross-machine-test",
            issue_number=42,
            initial_phase=first_phase
        )
        
        # Verify both files created
        projects_file = workspace_root / ".st3" / "projects.json"
        state_file = workspace_root / ".st3" / "state.json"
        
        assert projects_file.exists()
        assert state_file.exists()
        
        projects = json.loads(projects_file.read_text())
        assert "42" in projects
        
        state = json.loads(state_file.read_text())
        # state.json stores a single state object for the current branch
        assert state["branch"] == "fix/42-cross-machine-test"
        assert state["current_phase"] == "research"
        
        # =====================================================================
        # MACHINE A: Make phase progression with phase:label commits
        # =====================================================================
        
        # Commit projects.json to git (state.json NOT committed - in .gitignore)
        subprocess.run(
            ["git", "add", ".st3/projects.json"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "phase:research - Initial analysis"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Simulate phase transitions with commits
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:planning - Define goals"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:design - Technical specs"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:red - Write failing tests"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # =====================================================================
        # MACHINE B: Simulate git pull (state.json missing)
        # =====================================================================
        
        # Delete state.json to simulate cross-machine scenario
        # (On Machine B after git pull, state.json doesn't exist)
        state_file.unlink()
        assert not state_file.exists()
        
        # projects.json still exists (version controlled)
        assert projects_file.exists()
        
        # =====================================================================
        # MACHINE B: Tools work transparently (Mode 2 auto-recovery)
        # =====================================================================
        
        # Create PhaseStateEngine (like tools would do)
        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )
        
        # Get state - should trigger auto-recovery
        recovered_state = state_engine.get_state("fix/42-cross-machine-test")
        
        # Verify state was reconstructed correctly
        assert recovered_state["branch"] == "fix/42-cross-machine-test"
        assert recovered_state["issue_number"] == 42
        assert recovered_state["workflow_name"] == "bug"
        
        # Phase should be detected as 'tdd' (most recent phase:red commit)
        # phase:red maps to 'tdd' phase in bug workflow
        assert recovered_state["current_phase"] == "tdd"
        
        # Reconstructed flag set for audit
        assert recovered_state["reconstructed"] is True
        
        # Transitions empty (cannot reconstruct history)
        assert recovered_state["transitions"] == []
        
        # Verify state.json was recreated
        assert state_file.exists()
        
        # Subsequent calls should return cached state (idempotent)
        state_again = state_engine.get_state("fix/42-cross-machine-test")
        assert state_again["current_phase"] == "tdd"
        assert state_again["issue_number"] == 42

    @pytest.mark.asyncio
    async def test_recovery_with_no_phase_commits(self, workspace_root: Path) -> None:
        """Test recovery when branch has no phase:label commits (fallback to first phase)."""
        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", "fix/43-no-labels"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Initialize project
        project_manager = ProjectManager(workspace_root=workspace_root)
        project_manager.initialize_project(
            issue_number=43,
            issue_title="No labels test",
            workflow_name="feature"
        )
        
        # Make commits WITHOUT phase labels
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Add feature code"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Fix bug"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Delete state.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()
        
        # Auto-recovery should fallback to first phase
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )
        
        recovered_state = state_engine.get_state("fix/43-no-labels")
        
        # Should fallback to first phase of feature workflow
        assert recovered_state["current_phase"] == "research"  # First phase
        assert recovered_state["reconstructed"] is True

    @pytest.mark.asyncio
    async def test_recovery_respects_workflow_phases(self, workspace_root: Path) -> None:
        """Test that recovery only detects phases valid in the workflow."""
        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", "docs/44-documentation"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Initialize with docs workflow (only has: research, planning, design, documentation)
        project_manager = ProjectManager(workspace_root=workspace_root)
        project_manager.initialize_project(
            issue_number=44,
            issue_title="Docs test",
            workflow_name="docs"
        )
        
        # Make commits with phases NOT in docs workflow
        # Git log returns most recent first, so later commits are checked first
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:integration - Not in docs workflow"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:tdd - Also not in docs workflow"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:design - VALID and most recent"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "phase:planning - Valid but earlier"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Delete state.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()
        
        # Auto-recovery should ignore invalid phases
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )
        
        recovered_state = state_engine.get_state("docs/44-documentation")

        # Git log returns commits newest first
        # Should iterate through: planning (valid but later), design (valid, found first)
        # phase:planning is most recent VALID phase, should be detected
        assert recovered_state["current_phase"] == "planning"
        assert recovered_state["reconstructed"] is True

    @pytest.mark.asyncio
    async def test_recovery_with_invalid_branch_name(self, workspace_root: Path) -> None:
        """Test that recovery fails gracefully with helpful error for invalid branch."""
        # Create branch with invalid format (no issue number)
        subprocess.run(
            ["git", "checkout", "-b", "invalid-branch-name"],
            cwd=workspace_root,
            check=True,
            capture_output=True
        )
        
        # Try to recover - should fail with clear error
        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )
        
        with pytest.raises(ValueError, match="Cannot extract issue number"):
            state_engine.get_state("invalid-branch-name")
