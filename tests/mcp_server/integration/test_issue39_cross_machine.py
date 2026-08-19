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

from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
)


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
            ["git", "checkout", "-b", "bug/42-cross-machine-test"],
            cwd=workspace_root,
            check=True,
            capture_output=True,
        )

        # Initialize project (Mode 1 - atomic creation)
        project_manager = make_project_manager(workspace_root)
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "bug/42-cross-machine-test"

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
            branch="bug/42-cross-machine-test", issue_number=42, initial_phase=first_phase
        )

        # Verify deliverables register and branch state were created
        deliverables_file = workspace_root / get_default_server_root() / "deliverables.json"
        state_file = workspace_root / get_default_server_root() / "state.json"

        assert deliverables_file.exists()
        assert state_file.exists()

        deliverables = json.loads(deliverables_file.read_text())
        projects = deliverables.get("projects", deliverables)
        assert "42" in projects
        state = json.loads(state_file.read_text())
        assert state["branch"] == "bug/42-cross-machine-test"
        assert state["current_phase"] == "research"
