"""RED tests for force_phase_transition MCP tool.

Issue #50 - Step 4: Force Transition Tool

Tests MCP tool that exposes PhaseStateEngine.force_transition() to users.
Allows non-sequential phase transitions with skip_reason and approval.
Issue #229 Cycle 10: GAP-17 — blocking gates must appear BEFORE ✅ in response.
"""

import json
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
        return PhaseStateEngine(workspace_root=workspace_root, project_manager=project_manager)

    @pytest.fixture
    def tool(self, workspace_root: Path) -> ForcePhaseTransitionTool:
        """Create ForcePhaseTransitionTool instance."""
        return ForcePhaseTransitionTool(workspace_root=workspace_root)

    @pytest.fixture
    def initialized_branch(
        self,
        project_manager: ProjectManager,
        phase_engine: PhaseStateEngine,
        feature_phases: list[str],
    ) -> str:
        """Initialize a project and branch for testing."""
        # Initialize project
        project_manager.initialize_project(
            issue_number=42, issue_title="Test feature", workflow_name="feature"
        )

        # Initialize branch
        branch = "feature/42-test"
        phase_engine.initialize_branch(
            branch=branch,
            issue_number=42,
            initial_phase=feature_phases[0],  # discovery
        )

        return branch

    @pytest.mark.asyncio
    async def test_force_phase_transition_tool_success(
        self,
        tool: ForcePhaseTransitionTool,
        initialized_branch: str,
        phase_engine: PhaseStateEngine,
        feature_phases: list[str],
    ) -> None:
        """Test successful forced transition (discovery → design, skips planning)."""
        # Execute tool (force skip planning)
        params = ForcePhaseTransitionInput(
            branch=initialized_branch,
            to_phase=feature_phases[2],  # design
            skip_reason="Planning already done in previous project",
            human_approval="Approved: Skip planning phase",
        )

        result = await tool.execute(params)

        # Check result
        assert "✅" in result.content[0]["text"]
        assert feature_phases[0] in result.content[0]["text"]  # discovery
        assert feature_phases[2] in result.content[0]["text"]  # design
        assert "forced" in result.content[0]["text"].lower()

        # Verify state updated
        state = phase_engine.get_state(initialized_branch)
        assert state["current_phase"] == feature_phases[2]  # design

        # Verify transition marked as forced
        transition = state["transitions"][0]
        assert transition["forced"] is True
        assert transition["skip_reason"] == "Planning already done in previous project"

    def test_force_phase_transition_tool_requires_skip_reason(
        self, initialized_branch: str, feature_phases: list[str]
    ) -> None:
        """Test tool requires skip_reason parameter."""
        # Empty skip_reason should be rejected
        with pytest.raises(ValueError, match="cannot be empty"):
            ForcePhaseTransitionInput(
                branch=initialized_branch,
                to_phase=feature_phases[2],  # design
                skip_reason="",
                human_approval="Approved",
            )

    def test_force_phase_transition_tool_requires_human_approval(
        self, initialized_branch: str, feature_phases: list[str]
    ) -> None:
        """Test tool requires human_approval parameter."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ForcePhaseTransitionInput(
                branch=initialized_branch,
                to_phase=feature_phases[2],  # design
                skip_reason="Planning done",
                human_approval="",
            )

    @pytest.mark.asyncio
    async def test_force_phase_transition_tool_unknown_branch(
        self, tool: ForcePhaseTransitionTool, feature_phases: list[str]
    ) -> None:
        """Test tool handles unknown branch gracefully."""
        params = ForcePhaseTransitionInput(
            branch="feature/999-unknown",
            to_phase=feature_phases[2],  # design
            skip_reason="Testing error handling",
            human_approval="Approved",
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
        phase_engine: PhaseStateEngine,
        feature_phases: list[str],
    ) -> None:
        """Test tool allows any transition (even backward)."""
        # Move to planning first
        phase_engine.transition(
            branch=initialized_branch,
            to_phase=feature_phases[1],  # planning
            human_approval="Normal transition",
        )

        # Force backward transition (planning → discovery)
        params = ForcePhaseTransitionInput(
            branch=initialized_branch,
            to_phase=feature_phases[0],  # discovery (Backward!)
            skip_reason="Need to revisit discovery phase",
            human_approval="Approved: Return to discovery",
        )

        result = await tool.execute(params)

        # Check success
        assert "✅" in result.content[0]["text"]
        assert phase_engine.get_current_phase(initialized_branch) == feature_phases[0]  # discovery

    def test_force_phase_transition_tool_input_model_validation(
        self, feature_phases: list[str]
    ) -> None:
        """Test input model has correct field types and requirements."""
        # Valid input
        valid = ForcePhaseTransitionInput(
            branch="feature/42-test",
            to_phase=feature_phases[2],  # design
            skip_reason="Valid reason",
            human_approval="Approved",
        )

        assert valid.branch == "feature/42-test"
        assert valid.to_phase == feature_phases[2]  # design
        assert valid.skip_reason == "Valid reason"
        assert valid.human_approval == "Approved"


# ---------------------------------------------------------------------------
# C3 extension: skipped-gates warning surfaced in tool response (GAP-03 Optie 1)
# ---------------------------------------------------------------------------


class TestForcePhaseTransitionToolSkippedGatesResponse:
    """Test that tool response includes skipped-gates warning when gates are bypassed."""

    @pytest.fixture
    def workspace_with_gates(self, tmp_path: Path) -> Path:
        """Workspace with workphases.yaml that has exit_requires on planning."""
        st3 = tmp_path / ".st3"
        st3.mkdir()
        (st3 / "workphases.yaml").write_text(
            """
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
  design:
    display_name: "Design"
"""
        )
        return tmp_path

    @pytest.fixture
    def workspace_no_gates(self, tmp_path: Path) -> Path:
        """Workspace with workphases.yaml that has no gates defined."""
        st3 = tmp_path / ".st3"
        st3.mkdir()
        (st3 / "workphases.yaml").write_text(
            """
phases:
  planning:
    display_name: "Planning"
  design:
    display_name: "Design"
"""
        )
        return tmp_path

    def _init_branch(self, workspace: Path, branch: str, phase: str) -> None:
        """Helper: initialize project + branch state."""
        pm = ProjectManager(workspace_root=workspace)
        pm.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")
        engine = PhaseStateEngine(workspace_root=workspace, project_manager=pm)
        engine.initialize_branch(branch=branch, issue_number=42, initial_phase=phase)

    @pytest.mark.asyncio
    async def test_force_transition_tool_response_includes_skipped_gates_warning(
        self, workspace_with_gates: Path
    ) -> None:
        """Tool response includes ⚠️ skipped gates line when gates are bypassed (GAP-03)."""
        branch = "feature/42-test"
        self._init_branch(workspace_with_gates, branch, "planning")

        tool = ForcePhaseTransitionTool(workspace_root=workspace_with_gates)
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Emergency skip",
            human_approval="Michel approved on 2026-02-19",
        )

        result = await tool.execute(params)

        text = result.content[0]["text"]
        assert "✅" in text
        assert "⚠️" in text
        assert "skipped" in text.lower()
        assert "planning_deliverables" in text

    @pytest.mark.asyncio
    async def test_force_transition_tool_response_no_warning_when_no_gates(
        self, workspace_no_gates: Path
    ) -> None:
        """Tool response has no ⚠️ when neither phase has gates (GAP-03)."""
        branch = "feature/42-test"
        self._init_branch(workspace_no_gates, branch, "planning")

        tool = ForcePhaseTransitionTool(workspace_root=workspace_no_gates)
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Emergency skip",
            human_approval="Michel approved on 2026-02-19",
        )

        result = await tool.execute(params)

        text = result.content[0]["text"]
        assert "✅" in text
        assert "⚠️" not in text


# ---------------------------------------------------------------------------
# C10: GAP-17 — force transition response: blocking gates BEFORE ✅ (Issue #229)
# ---------------------------------------------------------------------------


class TestForceTransitionResponseFormat:
    """Blocking gates appear BEFORE ✅; passing gates appear AFTER ✅ (Issue #229 C10, GAP-17).

    D10.1: ⚠️ ACTION REQUIRED block emitted before ✅ when a gate would have blocked.
    D10.2: ℹ️ informational block emitted after ✅ when a gate would have passed.
    D10.3: No extra output when no gates defined.
    """

    def _setup_workspace(self, tmp_path: Path, *, with_gate_key: bool = True) -> tuple[Path, str]:
        """Build workspace with workphases.yaml gate + optional planning_deliverables key."""
        st3 = tmp_path / ".st3"
        st3.mkdir()
        (st3 / "workphases.yaml").write_text(
            """
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
  design:
    display_name: "Design"
"""
        )
        branch = "feature/42-test"
        pm = ProjectManager(workspace_root=tmp_path)
        pm.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=pm)
        engine.initialize_branch(branch=branch, issue_number=42, initial_phase="planning")

        if with_gate_key:
            # Inject planning_deliverables so gate would have PASSED
            projects_path = tmp_path / ".st3" / "projects.json"
            data = json.loads(projects_path.read_text())
            data["42"]["planning_deliverables"] = {"tdd_cycles": {"total": 1, "cycles": []}}
            projects_path.write_text(json.dumps(data, indent=2))

        return tmp_path, branch

    @pytest.mark.asyncio
    async def test_force_phase_transition_response_blocking_gate_appears_before_success(
        self, tmp_path: Path
    ) -> None:
        """Blocking gates (key absent) emit ⚠️ ACTION REQUIRED BEFORE ✅ (GAP-17/D10.1)."""
        workspace, branch = self._setup_workspace(
            tmp_path, with_gate_key=False
        )  # key absent → BLOCKS
        tool = ForcePhaseTransitionTool(workspace_root=workspace)
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Force test",
            human_approval="Approved",
        )

        result = await tool.execute(params)
        text = result.content[0]["text"]

        assert "ACTION REQUIRED" in text, f"Expected ACTION REQUIRED in response: {text}"
        assert "✅" in text
        # Blocking warning must appear BEFORE ✅
        assert text.index("ACTION REQUIRED") < text.index("✅"), (
            f"ACTION REQUIRED must precede ✅, got:\n{text}"
        )

    @pytest.mark.asyncio
    async def test_force_phase_transition_response_passing_gate_appears_after_success(
        self, tmp_path: Path
    ) -> None:
        """Passing gates (key present) emitted as informational text AFTER ✅ (GAP-17/D10.2)."""
        workspace, branch = self._setup_workspace(
            tmp_path, with_gate_key=True
        )  # key present → passes
        tool = ForcePhaseTransitionTool(workspace_root=workspace)
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Force test",
            human_approval="Approved",
        )

        result = await tool.execute(params)
        text = result.content[0]["text"]

        assert "✅" in text
        # planning_deliverables key should appear as informational AFTER ✅
        assert "planning_deliverables" in text, (
            f"Expected gate key in informational section: {text}"
        )
        assert text.index("✅") < text.index("planning_deliverables"), (
            f"Informational gate must follow ✅, got:\n{text}"
        )

    @pytest.mark.asyncio
    async def test_force_phase_transition_response_no_gates_no_warning(
        self, tmp_path: Path
    ) -> None:
        """No gates defined → only ✅ in response, no ⚠️ or ACTION REQUIRED (GAP-17/D10.3)."""
        st3 = tmp_path / ".st3"
        st3.mkdir()
        (st3 / "workphases.yaml").write_text(
            """
phases:
  planning:
    display_name: "Planning"
  design:
    display_name: "Design"
"""
        )
        branch = "feature/42-test"
        pm = ProjectManager(workspace_root=tmp_path)
        pm.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=pm)
        engine.initialize_branch(branch=branch, issue_number=42, initial_phase="planning")

        tool = ForcePhaseTransitionTool(workspace_root=tmp_path)
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Force test",
            human_approval="Approved",
        )

        result = await tool.execute(params)
        text = result.content[0]["text"]

        assert "✅" in text
        assert "ACTION REQUIRED" not in text, f"Unexpected ACTION REQUIRED: {text}"
        assert "⚠️" not in text, f"Unexpected ⚠️: {text}"
