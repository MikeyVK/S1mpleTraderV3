"""Integration tests for Issue #39: Cross-machine state recovery.

Tests the complete flow:
1. Machine A: Initialize project (Mode 1 - creates deliverables.json + state.json)
2. Machine A: Make commits with Conventional Commit scopes
3. Machine A: Push to git
4. Machine B: Pull code (state.json missing - not in git)
5. Machine B: Tools work transparently (Mode 2 - auto-recovery)

This validates that the dual-mode system works end-to-end across machines.

@layer: Tests (Integration)
@dependencies: [pytest, subprocess, tests.mcp_server.test_support]
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager


class TestIssue39CrossMachine:
    """Integration tests for cross-machine state recovery."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace with git repo."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        readme = workspace / "README.md"
        readme.write_text("# Test Project")
        subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace,
            check=True,
            capture_output=True,
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
            capture_output=True,
        )

        # Initialize project (Mode 1 - atomic creation)
        project_manager = make_project_manager(workspace_root)
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "fix/42-cross-machine-test"

        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        # Initialize project atomically (Mode 1)
        project_manager.initialize_project(
            issue_number=42, issue_title="Cross-machine test", workflow_name="bug"
        )

        # Get first phase from workflow
        result = project_manager.get_project_plan(42)
        assert result is not None
        first_phase = result["required_phases"][0]

        # Initialize state
        state_engine.initialize_branch(
            branch="fix/42-cross-machine-test", issue_number=42, initial_phase=first_phase
        )

        # Verify deliverables register and branch state were created
        deliverables_file = workspace_root / ".st3" / "deliverables.json"
        state_file = workspace_root / ".st3" / "state.json"

        assert deliverables_file.exists()
        assert state_file.exists()

        deliverables = json.loads(deliverables_file.read_text())
        assert "42" in deliverables

        state = json.loads(state_file.read_text())
        assert state["branch"] == "fix/42-cross-machine-test"
        assert state["current_phase"] == "research"

        # =====================================================================
        # MACHINE A: Make phase progression with Conventional Commit scopes
        # =====================================================================

        # Commit deliverables.json to git (state.json NOT committed - in .gitignore)
        subprocess.run(
            ["git", "add", ".st3/deliverables.json"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "docs(P_RESEARCH): Initial analysis"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Simulate phase transitions with commits
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "docs(P_PLANNING): Define goals"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "docs(P_DESIGN): Technical specs"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "--allow-empty",
                "-m",
                "test(P_IMPLEMENTATION_SP_RED): Write failing tests",
            ],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # =====================================================================
        # MACHINE B: Simulate git pull (state.json missing)
        # =====================================================================

        # Delete state.json to simulate cross-machine scenario
        # (On Machine B after git pull, state.json doesn't exist)
        state_file.unlink()
        assert not state_file.exists()

        # deliverables.json still exists (version controlled)
        assert deliverables_file.exists()

        # =====================================================================
        # MACHINE B: Tools work transparently (Mode 2 auto-recovery)
        # =====================================================================

        # Create PhaseStateEngine (like tools would do)
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        # Pure-query contract: missing state.json must not auto-reconstruct via get_state().
        with pytest.raises(FileNotFoundError):
            state_engine.get_state("fix/42-cross-machine-test")

        # Recovery is triggered on the transition path.
        recovery_result = state_engine.force_transition(
            branch="fix/42-cross-machine-test",
            to_phase="integration",
            skip_reason="Trigger cross-machine recovery",
            human_approval="Verifier approved on 2026-04-05",
        )

        # Verify recovery inferred the pre-transition state correctly.
        assert recovery_result["from_phase"] == "implementation"
        assert recovery_result["to_phase"] == "integration"

        recovered_state = state_engine.get_state("fix/42-cross-machine-test")
        assert recovered_state.branch == "fix/42-cross-machine-test"
        assert recovered_state.issue_number == 42
        assert recovered_state.workflow_name == "bug"
        assert recovered_state.current_phase == "integration"
        assert recovered_state.reconstructed is True

        # Verify state.json was recreated
        assert state_file.exists()

        # Subsequent calls should return persisted state (idempotent)
        state_again = state_engine.get_state("fix/42-cross-machine-test")
        assert state_again.current_phase == "integration"
        assert state_again.issue_number == 42

    @pytest.mark.asyncio
    async def test_recovery_with_no_phase_commits(self, workspace_root: Path) -> None:
        """Test fallback when a branch has no commit-scope phase commits."""
        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", "fix/43-no-labels"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Initialize project
        project_manager = make_project_manager(workspace_root)
        project_manager.initialize_project(
            issue_number=43, issue_title="No labels test", workflow_name="feature"
        )

        # Make commits WITHOUT phase labels
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Add feature code"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "Fix bug"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Delete state.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Recovery now happens only on transition paths.
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        with pytest.raises(FileNotFoundError):
            state_engine.get_state("fix/43-no-labels")

        recovery_result = state_engine.force_transition(
            branch="fix/43-no-labels",
            to_phase="planning",
            skip_reason="Trigger recovery without scoped commits",
            human_approval="Verifier approved on 2026-04-05",
        )

        # Recovery should fallback to the first phase of the workflow.
        assert recovery_result["from_phase"] == "research"

        recovered_state = state_engine.get_state("fix/43-no-labels")
        assert recovered_state.current_phase == "planning"
        assert recovered_state.reconstructed is True

    @pytest.mark.asyncio
    async def test_recovery_respects_workflow_phases(self, workspace_root: Path) -> None:
        """Test that recovery only detects phases valid in the workflow."""
        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", "docs/44-documentation"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Initialize with docs workflow (only has: research, planning, design, documentation)
        project_manager = make_project_manager(workspace_root)
        project_manager.initialize_project(
            issue_number=44, issue_title="Docs test", workflow_name="docs"
        )

        # Make commits with phases NOT in docs workflow
        # Git log returns most recent first, so later commits are checked first
        subprocess.run(
            [
                "git",
                "commit",
                "--allow-empty",
                "-m",
                "docs(P_INTEGRATION): Not in docs workflow",
            ],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "--allow-empty",
                "-m",
                "docs(P_IMPLEMENTATION): Also not in docs workflow",
            ],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "docs(P_DESIGN): VALID and most recent"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "docs(P_PLANNING): Valid but earlier"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Delete state.json
        state_file = workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_file.unlink()

        # Recovery now happens only on transition paths.
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        with pytest.raises(FileNotFoundError):
            state_engine.get_state("docs/44-documentation")

        recovery_result = state_engine.force_transition(
            branch="docs/44-documentation",
            to_phase="documentation",
            skip_reason="Trigger recovery for docs workflow",
            human_approval="Verifier approved on 2026-04-05",
        )

        # Git log returns commits newest first.
        # P_PLANNING is the most recent valid phase in the docs workflow.
        assert recovery_result["from_phase"] == "planning"

        recovered_state = state_engine.get_state("docs/44-documentation")
        assert recovered_state.current_phase == "documentation"
        assert recovered_state.reconstructed is True

    @pytest.mark.asyncio
    async def test_recovery_with_invalid_branch_name(self, workspace_root: Path) -> None:
        """Test that get_state() remains a pure query for invalid branches."""
        # Create branch with invalid format (no issue number)
        subprocess.run(
            ["git", "checkout", "-b", "invalid-branch-name"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Pure-query contract: loading missing state should surface the repository error.
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        with pytest.raises(FileNotFoundError):
            state_engine.get_state("invalid-branch-name")
