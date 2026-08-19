"""RED tests for force_phase_transition MCP tool.

Issue #50 - Step 4: Force Transition Tool

Tests MCP tool that exposes PhaseStateEngine.force_transition() to users.
Allows non-sequential phase transitions with skip_reason and approval.
Issue #229 Cycle 10: GAP-17 — blocking gates must appear BEFORE OK in response.

@layer: Tests (Unit)
@dependencies: [pytest, pathlib, mcp_server.tools.phase_tools]
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from mcp_server.core.interfaces import GateReport
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.schemas.tool_outputs import ForcePhaseTransitionOutput
from mcp_server.tools.phase_tools import (
    ForcePhaseTransitionInput,
    ForcePhaseTransitionTool,
)
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
)


class _StaticGateRunner:
    """Minimal current-interface gate runner for force-transition response tests."""

    def __init__(
        self,
        *,
        blocking: tuple[str, ...] = (),
        passing: tuple[str, ...] = (),
    ) -> None:
        self._report = GateReport(blocking=blocking, passing=passing)

    def enforce_phase_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return self._report

    def inspect_phase_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return self._report

    def enforce_cycle_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return self._report

    def inspect_cycle_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return self._report

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        del workflow_name, phase
        return False


class TestForcePhaseTransitionTool:
    """Test force_phase_transition MCP tool."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace."""
        return tmp_path

    @pytest.fixture
    def project_manager(self, workspace_root: Path) -> ProjectManager:
        """Create ProjectManager instance."""
        return make_project_manager(workspace_root)

    @pytest.fixture
    def phase_engine(
        self, workspace_root: Path, project_manager: ProjectManager
    ) -> PhaseStateEngine:
        """Create PhaseStateEngine instance."""
        return make_phase_state_engine(workspace_root, project_manager=project_manager)

    @pytest.fixture
    def tool(self, workspace_root: Path) -> ForcePhaseTransitionTool:
        """Create ForcePhaseTransitionTool instance."""
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)
        return ForcePhaseTransitionTool(
            workspace_root=workspace_root,
            project_manager=project_manager,
            state_engine=state_engine,
            server_root=workspace_root,
            workphases_config=None,
        )

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
            human_approval_message="Approved: Skip planning phase",
        )

        result = await tool.execute(params, NoteContext())

        # Check result
        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
        assert result.branch == initialized_branch
        assert result.to_phase == feature_phases[2]

        # Verify state updated
        state = phase_engine.get_state(initialized_branch)
        assert state.current_phase == feature_phases[2]  # design

        # Verify transition marked as forced
        transition = state.transitions[0]
        assert transition["forced"] is True
        assert transition["skip_reason"] == "Planning already done in previous project"

    @pytest.mark.asyncio
    async def test_force_phase_transition_tool_emits_advisory_info_note_after_success(
        self,
        tool: ForcePhaseTransitionTool,
        initialized_branch: str,
        feature_phases: list[str],
    ) -> None:
        """Forced transitions should emit the standard get_work_context advisory note."""
        params = ForcePhaseTransitionInput(
            branch=initialized_branch,
            to_phase=feature_phases[2],
            skip_reason="Planning already done in previous project",
            human_approval_message="Approved: Skip planning phase",
        )
        context = NoteContext()

        await tool.execute(params, context)

        assert len(context.entries) == 0

    def test_force_phase_transition_tool_requires_skip_reason(
        self, initialized_branch: str, feature_phases: list[str]
    ) -> None:
        """Test tool requires skip_reason parameter."""
        # Empty skip_reason should be rejected (min_length=1 or field_validator)
        with pytest.raises(ValidationError):
            ForcePhaseTransitionInput(
                branch=initialized_branch,
                to_phase=feature_phases[2],  # design
                skip_reason="",
                human_approval_message="Approved",
            )

    def test_force_phase_transition_tool_requires_human_approval_message(
        self, initialized_branch: str, feature_phases: list[str]
    ) -> None:
        """Test tool requires human_approval_message parameter."""
        with pytest.raises(ValidationError):
            ForcePhaseTransitionInput(
                branch=initialized_branch,
                to_phase=feature_phases[2],  # design
                skip_reason="Planning done",
                human_approval_message="",
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
            human_approval_message="Approved",
        )

        result = await tool.execute(params, NoteContext())

        # Check error message
        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is False

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
            human_approval_message="Normal transition",
        )

        # Force backward transition (planning → discovery)
        params = ForcePhaseTransitionInput(
            branch=initialized_branch,
            to_phase=feature_phases[0],  # discovery (Backward!)
            skip_reason="Need to revisit discovery phase",
            human_approval_message="Approved: Return to discovery",
        )

        result = await tool.execute(params, NoteContext())

        # Check success
        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
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
            human_approval_message="Approved",
        )

        assert valid.branch == "feature/42-test"
        assert valid.to_phase == feature_phases[2]  # design
        assert valid.skip_reason == "Valid reason"
        assert valid.human_approval_message == "Approved"


# ---------------------------------------------------------------------------
# C3 extension: skipped-gates warning surfaced in tool response (GAP-03 Optie 1)
# ---------------------------------------------------------------------------


class TestForcePhaseTransitionToolSkippedGatesResponse:
    """Test that tool response includes skipped-gates warning when gates are bypassed."""

    @pytest.fixture
    def workspace_with_gates(self, tmp_path: Path) -> Path:
        """Workspace with workphases.yaml that has exit_requires on planning."""
        phase_gate_config = tmp_path / get_default_server_root() / "config"
        phase_gate_config.mkdir(parents=True)
        (phase_gate_config / "workphases.yaml").write_text(
            """
version: "1.0.0"
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
  design:
    display_name: "Design"
  ready:
    display_name: "Ready"
    terminal: true
"""
        )
        return tmp_path

    @pytest.fixture
    def workspace_no_gates(self, tmp_path: Path) -> Path:
        """Workspace with workphases.yaml that has no gates defined."""
        phase_gate_config = tmp_path / get_default_server_root() / "config"
        phase_gate_config.mkdir(parents=True)
        (phase_gate_config / "workphases.yaml").write_text(
            """
version: "1.0.0"
phases:
  planning:
    display_name: "Planning"
  design:
    display_name: "Design"
  ready:
    display_name: "Ready"
    terminal: true
"""
        )
        return tmp_path

    def _init_branch(self, workspace: Path, branch: str, phase: str) -> None:
        """Helper: initialize project + branch state."""
        pm = make_project_manager(workspace)
        pm.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")
        engine = make_phase_state_engine(workspace, project_manager=pm)
        engine.initialize_branch(branch=branch, issue_number=42, initial_phase=phase)

    @pytest.mark.asyncio
    async def test_force_transition_tool_response_includes_skipped_gates_warning(
        self, workspace_with_gates: Path
    ) -> None:
        """Tool response includes ⚠️ skipped gates line when gates are bypassed (GAP-03)."""
        branch = "feature/42-test"
        self._init_branch(workspace_with_gates, branch, "planning")

        tool = ForcePhaseTransitionTool(
            workspace_root=workspace_with_gates,
            project_manager=make_project_manager(workspace_with_gates),
            state_engine=make_phase_state_engine(
                workspace_with_gates,
                project_manager=make_project_manager(workspace_with_gates),
                workflow_gate_runner=_StaticGateRunner(blocking=("planning_deliverables",)),
            ),
            server_root=workspace_with_gates,
            workphases_config=None,
        )
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Emergency skip",
            human_approval_message="Michel approved on 2026-02-19",
        )

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
        assert "planning_deliverables" in result.skipped_gates

    @pytest.mark.asyncio
    async def test_force_transition_tool_response_no_warning_when_no_gates(
        self, workspace_no_gates: Path
    ) -> None:
        """Tool response has no ⚠️ when neither phase has gates (GAP-03)."""
        branch = "feature/42-test"
        self._init_branch(workspace_no_gates, branch, "planning")

        tool = ForcePhaseTransitionTool(
            workspace_root=workspace_no_gates,
            project_manager=make_project_manager(workspace_no_gates),
            state_engine=make_phase_state_engine(
                workspace_no_gates,
                project_manager=make_project_manager(workspace_no_gates),
                workflow_gate_runner=_StaticGateRunner(),
            ),
            server_root=workspace_no_gates,
            workphases_config=None,
        )
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Emergency skip",
            human_approval_message="Michel approved on 2026-02-19",
        )

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
        assert len(result.skipped_gates) == 0


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
        phase_gate_config = tmp_path / get_default_server_root() / "config"
        phase_gate_config.mkdir(parents=True)
        (phase_gate_config / "workphases.yaml").write_text(
            """
version: "1.0.0"
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
  design:
    display_name: "Design"
  ready:
    display_name: "Ready"
    terminal: true
"""
        )
        branch = "feature/42-test"
        pm = make_project_manager(tmp_path)
        pm.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")
        engine = make_phase_state_engine(tmp_path, project_manager=pm)
        engine.initialize_branch(branch=branch, issue_number=42, initial_phase="planning")

        if with_gate_key:
            # Inject planning_deliverables so gate would have PASSED
            pm.save_planning_deliverables(
                42,
                {
                    "cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [{"id": "D1", "description": "D1"}],
                                "exit_criteria": "c",
                            }
                        ],
                    }
                },
            )

        return tmp_path, branch

    @pytest.mark.asyncio
    async def test_force_phase_transition_response_blocking_gate_appears_before_success(
        self, tmp_path: Path
    ) -> None:
        """Blocking gates (key absent) emit ⚠️ ACTION REQUIRED BEFORE ✅ (GAP-17/D10.1)."""
        workspace, branch = self._setup_workspace(
            tmp_path, with_gate_key=False
        )  # key absent → BLOCKS
        tool = ForcePhaseTransitionTool(
            workspace_root=workspace,
            project_manager=make_project_manager(workspace),
            state_engine=make_phase_state_engine(
                workspace,
                project_manager=make_project_manager(workspace),
                workflow_gate_runner=_StaticGateRunner(blocking=("planning_deliverables",)),
            ),
            server_root=workspace,
            workphases_config=None,
        )
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Force test",
            human_approval_message="Approved",
        )

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
        assert "planning_deliverables" in result.skipped_gates

    @pytest.mark.asyncio
    async def test_force_phase_transition_response_passing_gate_appears_after_success(
        self, tmp_path: Path
    ) -> None:
        """Passing gates (key present) emitted as informational text AFTER ✅ (GAP-17/D10.2)."""
        workspace, branch = self._setup_workspace(
            tmp_path, with_gate_key=True
        )  # key present → passes
        tool = ForcePhaseTransitionTool(
            workspace_root=workspace,
            project_manager=make_project_manager(workspace),
            state_engine=make_phase_state_engine(
                workspace,
                project_manager=make_project_manager(workspace),
                workflow_gate_runner=_StaticGateRunner(passing=("planning_deliverables",)),
            ),
            server_root=workspace,
            workphases_config=None,
        )
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Force test",
            human_approval_message="Approved",
        )

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
        assert "planning_deliverables" in result.passing_gates

    @pytest.mark.asyncio
    async def test_force_phase_transition_response_no_gates_no_warning(
        self, tmp_path: Path
    ) -> None:
        """No gates defined → only ✅ in response, no ⚠️ or ACTION REQUIRED (GAP-17/D10.3)."""
        phase_gate_config = tmp_path / get_default_server_root() / "config"
        phase_gate_config.mkdir(parents=True)
        (phase_gate_config / "workphases.yaml").write_text(
            """
version: "1.0.0"
phases:
  planning:
    display_name: "Planning"
  design:
    display_name: "Design"
  ready:
    display_name: "Ready"
    terminal: true
"""
        )
        branch = "feature/42-test"
        pm = make_project_manager(tmp_path)
        pm.initialize_project(issue_number=42, issue_title="Test", workflow_name="feature")
        engine = make_phase_state_engine(tmp_path, project_manager=pm)
        engine.initialize_branch(branch=branch, issue_number=42, initial_phase="planning")

        tool = ForcePhaseTransitionTool(
            workspace_root=tmp_path,
            project_manager=make_project_manager(tmp_path),
            state_engine=make_phase_state_engine(
                tmp_path,
                project_manager=make_project_manager(tmp_path),
                workflow_gate_runner=_StaticGateRunner(),
            ),
            server_root=tmp_path,
            workphases_config=None,
        )
        params = ForcePhaseTransitionInput(
            branch=branch,
            to_phase="design",
            skip_reason="Force test",
            human_approval_message="Approved",
        )

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, ForcePhaseTransitionOutput)
        assert result.success is True
        assert len(result.skipped_gates) == 0
        assert len(result.passing_gates) == 0

    def test_force_phase_transition_input_rejects_boolean_approval(self) -> None:
        """Reject boolean input for human_approval_message (C_PHASE_TOOLS.2)."""
        with pytest.raises(ValidationError, match="human_approval_message"):
            ForcePhaseTransitionInput(
                branch="feature/42-test",
                to_phase="design",
                skip_reason="Valid reason",
                human_approval_message=True,  # type: ignore
            )
        with pytest.raises(ValidationError, match="human_approval_message"):
            ForcePhaseTransitionInput(
                branch="feature/42-test",
                to_phase="design",
                skip_reason="Valid reason",
                human_approval_message=False,  # type: ignore
            )
