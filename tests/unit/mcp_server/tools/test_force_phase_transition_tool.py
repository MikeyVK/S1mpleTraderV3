"""RED tests for force_phase_transition MCP tool.

Issue #50 - Step 4: Force Transition Tool

Tests MCP tool that exposes PhaseStateEngine.force_transition() to users.
Allows non-sequential phase transitions with skip_reason and approval.
"""
from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.phase_tools import (
    ForcePhaseTransitionInput,
    ForcePhaseTransitionTool,
)


class TestForcePhaseTransitionTool:
    """Test force_phase_transition MCP tool."""

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

    @pytest.fixture
    def tool(self, workspace_root: Path) -> ForcePhaseTransitionTool:
        """Create ForcePhaseTransitionTool instance."""
        return ForcePhaseTransitionTool(workspace_root=workspace_root)

    @pytest.fixture
    def initialized_branch(
        self,
        project_manager: ProjectManager,
        phase_engine: PhaseStateEngine
    ) -> str:
        """Initialize a project and branch for testing."""
        # Initialize project
        project_manager.initialize_project(
            issue_number=42,
            issue_title="Test feature",
            workflow_name="feature"
        )

        # Initialize branch
        branch = "feature/42-test"
        phase_engine.initialize_branch(
            branch=branch,
            issue_number=42,
            initial_phase="discovery"
        )

        return branch

    @pytest.mark.asyncio
    async def test_force_phase_transition_tool_success(
        self,
        tool: ForcePhaseTransitionTool,
        initialized_branch: str,
        phase_engine: PhaseStateEngine
    ) -> None:
        """Test successful forced transition (discovery → design, skips planning)."""
        # Execute tool (force skip planning)
        params = ForcePhaseTransitionInput(
            branch=initialized_branch,
            to_phase="design",
            skip_reason="Planning already done in previous project",
            human_approval="Approved: Skip planning phase"
        )

        result = await tool.execute(params)

        # Check result
        assert "✅" in result.content[0]["text"]
        assert "discovery" in result.content[0]["text"]
        assert "design" in result.content[0]["text"]
        assert "forced" in result.content[0]["text"].lower()

        # Verify state updated
        state = phase_engine.get_state(initialized_branch)
        assert state["current_phase"] == "design"

        # Verify transition marked as forced
        transition = state["transitions"][0]
        assert transition["forced"] is True
        assert transition["skip_reason"] == "Planning already done in previous project"

    def test_force_phase_transition_tool_requires_skip_reason(
        self,
        initialized_branch: str
    ) -> None:
        """Test tool requires skip_reason parameter."""
        # Empty skip_reason should be rejected
        with pytest.raises(ValueError, match="cannot be empty"):
            ForcePhaseTransitionInput(
                branch=initialized_branch,
                to_phase="design",
                skip_reason="",
                human_approval="Approved"
            )

    def test_force_phase_transition_tool_requires_human_approval(
        self,
        initialized_branch: str
    ) -> None:
        """Test tool requires human_approval parameter."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ForcePhaseTransitionInput(
                branch=initialized_branch,
                to_phase="design",
                skip_reason="Planning done",
                human_approval=""
            )

    @pytest.mark.asyncio
    async def test_force_phase_transition_tool_unknown_branch(
        self,
        tool: ForcePhaseTransitionTool
    ) -> None:
        """Test tool handles unknown branch gracefully."""
        params = ForcePhaseTransitionInput(
            branch="feature/999-unknown",
            to_phase="design",
            skip_reason="Testing error handling",
            human_approval="Approved"
        )

        result = await tool.execute(params)

        # Check error message
        assert "❌" in result.content[0]["text"]
        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_force_phase_transition_tool_allows_any_transition(
        self,
        tool: ForcePhaseTransitionTool,
        initialized_branch: str,
        phase_engine: PhaseStateEngine
    ) -> None:
        """Test tool allows any transition (even backward)."""
        # Move to planning first
        phase_engine.transition(
            branch=initialized_branch,
            to_phase="planning",
            human_approval="Normal transition"
        )

        # Force backward transition (planning → discovery)
        params = ForcePhaseTransitionInput(
            branch=initialized_branch,
            to_phase="discovery",  # Backward!
            skip_reason="Need to revisit discovery phase",
            human_approval="Approved: Return to discovery"
        )

        result = await tool.execute(params)

        # Check success
        assert "✅" in result.content[0]["text"]
        assert phase_engine.get_current_phase(initialized_branch) == "discovery"

    def test_force_phase_transition_tool_input_model_validation(
        self
    ) -> None:
        """Test input model has correct field types and requirements."""
        # Valid input
        valid = ForcePhaseTransitionInput(
            branch="feature/42-test",
            to_phase="design",
            skip_reason="Valid reason",
            human_approval="Approved"
        )

        assert valid.branch == "feature/42-test"
        assert valid.to_phase == "design"
        assert valid.skip_reason == "Valid reason"
        assert valid.human_approval == "Approved"
