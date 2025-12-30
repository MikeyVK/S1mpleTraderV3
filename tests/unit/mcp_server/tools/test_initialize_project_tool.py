"""Tests for InitializeProjectTool with atomic state initialization.

Issue #39: Mode 1 - Atomic initialization of projects.json + state.json.

Tests verify:
1. Both files created atomically
2. Branch name auto-detected from git
3. First phase determined from workflow
4. state.json properly initialized with correct structure
5. Error handling when git or state creation fails
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.config.workflows import workflow_config
from mcp_server.tools.project_tools import InitializeProjectInput, InitializeProjectTool


class TestInitializeProjectToolMode1:
    """Test atomic initialization (Mode 1) for Issue #39."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def tool(self, workspace_root: Path) -> InitializeProjectTool:
        """Create InitializeProjectTool instance."""
        return InitializeProjectTool(workspace_root=workspace_root)

    @pytest.mark.asyncio
    async def test_atomic_creation_both_files(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test that both projects.json AND state.json are created atomically.

        Issue #39 Gap 1: InitializeProjectTool only created projects.json.
        After fix: Must create both files in single operation.
        """
        # Mock git to return branch name on tool's git_manager instance
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.return_value = "fix/39-initialize-project-tool"

            # Execute initialization
            params = InitializeProjectInput(
                issue_number=39,
                issue_title="Fix initialization gap",
                workflow_name="bug"
            )
            result = await tool.execute(params)

            # Verify success
            assert not result.is_error

            # Verify projects.json created
            projects_file = workspace_root / ".st3" / "projects.json"
            assert projects_file.exists(), "projects.json must be created"

            # Verify state.json created
            state_file = workspace_root / ".st3" / "state.json"
            assert state_file.exists(), "state.json must be created (Issue #39 fix)"

            # Verify projects.json structure
            projects = json.loads(projects_file.read_text())
            assert "39" in projects
            assert projects["39"]["workflow_name"] == "bug"

            # Verify state.json structure
            states = json.loads(state_file.read_text())
            assert "fix/39-initialize-project-tool" in states
            state = states["fix/39-initialize-project-tool"]

            assert state["branch"] == "fix/39-initialize-project-tool"
            assert state["issue_number"] == 39
            assert state["workflow_name"] == "bug"
            # First phase from workflows.yaml (SSOT)
            bug_workflow = workflow_config.get_workflow("bug")
            expected_first_phase = bug_workflow.phases[0]
            assert state["current_phase"] == expected_first_phase
            assert state["transitions"] == []
            assert "created_at" in state
            # Not reconstructed, freshly created
            assert "reconstructed" not in state

    @pytest.mark.asyncio
    async def test_branch_name_auto_detected(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test that branch name is auto-detected from GitManager."""
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.return_value = "feature/42-user-auth"

            params = InitializeProjectInput(
                issue_number=42,
                issue_title="Add user authentication",
                workflow_name="feature"
            )
            result = await tool.execute(params)

            assert not result.is_error

            # Verify state uses detected branch
            state_file = workspace_root / ".st3" / "state.json"
            states = json.loads(state_file.read_text())
            assert "feature/42-user-auth" in states

            # Verify GitManager was called
            mock_git.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_phase_from_workflow(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test that initial phase is set to workflow's first phase."""
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.return_value = "hotfix/99-security"

            params = InitializeProjectInput(
                issue_number=99,
                issue_title="Security fix",
                workflow_name="hotfix"
            )
            result = await tool.execute(params)

            assert not result.is_error

            state_file = workspace_root / ".st3" / "state.json"
            states = json.loads(state_file.read_text())
            state = states["hotfix/99-security"]

            # First phase from workflows.yaml (SSOT)
            hotfix_workflow = workflow_config.get_workflow("hotfix")
            expected_first_phase = hotfix_workflow.phases[0]
            assert state["current_phase"] == expected_first_phase

    @pytest.mark.asyncio
    async def test_all_workflow_types_supported(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test atomic initialization works for all workflow types.

        Uses workflows.yaml as SSOT for expected first phases.
        """
        workflows_to_test = ["feature", "bug", "docs", "refactor", "hotfix"]

        for workflow_name in workflows_to_test:
            # Get expected first phase from workflows.yaml (SSOT)
            workflow = workflow_config.get_workflow(workflow_name)
            expected_first_phase = workflow.phases[0]

            # Determine branch prefix from workflow name
            branch_prefix_map = {
                "feature": "feature",
                "bug": "fix",
                "docs": "docs",
                "refactor": "refactor",
                "hotfix": "hotfix"
            }
            prefix = branch_prefix_map[workflow_name]
            issue_num = workflows_to_test.index(workflow_name) + 1
            branch = f"{prefix}/{issue_num}-test"

            # Clear state between tests
            state_file = workspace_root / ".st3" / "state.json"
            if state_file.exists():
                state_file.unlink()

            with patch.object(tool.git_manager, "get_current_branch") as mock_git:
                mock_git.return_value = branch

                params = InitializeProjectInput(
                    issue_number=issue_num,
                    issue_title=f"Test {workflow_name}",
                    workflow_name=workflow_name
                )
                result = await tool.execute(params)

                assert not result.is_error, f"{workflow_name} workflow must work"

                states = json.loads(state_file.read_text())
                state = states[branch]
                assert state["current_phase"] == expected_first_phase, \
                    f"{workflow_name} must start at {expected_first_phase} " \
                    f"(from workflows.yaml)"

    @pytest.mark.asyncio
    async def test_error_handling_git_failure(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test error handling when GitManager fails to get branch."""
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.side_effect = RuntimeError("Not a git repository")

            params = InitializeProjectInput(
                issue_number=39,
                issue_title="Test error",
                workflow_name="bug"
            )
            result = await tool.execute(params)

            # Should return error result
            assert result.is_error

    @pytest.mark.asyncio
    async def test_error_handling_state_creation_failure(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test error handling when state.json creation fails."""
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.return_value = "fix/39-test"

            with patch.object(tool.state_engine, "initialize_branch") as mock_init:
                mock_init.side_effect = OSError("Permission denied")

                params = InitializeProjectInput(
                    issue_number=39,
                    issue_title="Test error",
                    workflow_name="bug"
                )
                result = await tool.execute(params)

                # Should return error result
                assert result.is_error

    @pytest.mark.asyncio
    async def test_no_breaking_changes_to_projects_json(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test that projects.json format has core expected fields."""
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.return_value = "fix/39-test"

            params = InitializeProjectInput(
                issue_number=39,
                issue_title="Test format",
                workflow_name="bug"
            )
            result = await tool.execute(params)

            assert not result.is_error

            # Verify projects.json has core required fields
            projects_file = workspace_root / ".st3" / "projects.json"
            projects = json.loads(projects_file.read_text())
            project = projects["39"]

            # Core required fields must exist
            required_fields = {"workflow_name", "required_phases", "execution_mode"}
            assert required_fields.issubset(project.keys()), \
                f"Missing required fields: {required_fields - set(project.keys())}"

    @pytest.mark.asyncio
    async def test_state_json_not_in_projects_json(
        self, tool: InitializeProjectTool, workspace_root: Path
    ) -> None:
        """Test that state.json is separate file, not embedded in projects.json."""
        with patch.object(tool.git_manager, "get_current_branch") as mock_git:
            mock_git.return_value = "fix/39-test"

            params = InitializeProjectInput(
                issue_number=39,
                issue_title="Test separation",
                workflow_name="bug"
            )
            result = await tool.execute(params)

            assert not result.is_error

            # Verify separation
            projects_file = workspace_root / ".st3" / "projects.json"
            state_file = workspace_root / ".st3" / "state.json"

            assert projects_file.exists()
            assert state_file.exists()

            # state.json should NOT be mentioned in projects.json
            projects_content = projects_file.read_text()
            assert "state.json" not in projects_content
            # State field, not policy field
            assert "current_phase" not in projects_content
