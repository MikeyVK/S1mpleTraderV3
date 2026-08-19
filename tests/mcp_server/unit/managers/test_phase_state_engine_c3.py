"""Tests for PhaseStateEngine force_transition skipped-gate warning (Issue #229 Cycle 3).

GAP-03: Forced transitions bypass all hooks and deliverable checks with no warning.

C3 Deliverables:
  D3.1: force_transition logs warning listing skipped_gates when gates exist.

@layer: Tests (Unit)
@dependencies: pytest, tests.mcp_server.test_support, mcp_server.managers.phase_state_engine
"""

import logging
from pathlib import Path

import pytest

from mcp_server.core.interfaces import GateReport
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
)


class _StaticGateRunner:
    """Minimal current-interface gate runner for force-transition warning tests."""

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


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Workspace root with .pgmcp/config/workphases.yaml
    containing exit_requires + entry_expects.
    """
    config_dir = tmp_path / get_default_server_root() / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "workphases.yaml").write_text(
        """
version: "1.0.0"
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
  implementation:
    display_name: "Implementation"
    entry_expects:
      - key: "planning_deliverables"
        description: "Expected from planning"
  design:
    display_name: "Design"
  research:
    display_name: "Research"
  ready:
    display_name: "Ready"
    terminal: true
"""
    )
    return tmp_path


@pytest.fixture
def workspace_root_no_gates(tmp_path: Path) -> Path:
    """Workspace root with .pgmcp/config/workphases.yaml where phases have no gates."""
    config_dir = tmp_path / get_default_server_root() / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "workphases.yaml").write_text(
        """
version: "1.0.0"
phases:
  research:
    display_name: "Research"
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


@pytest.fixture
def project_manager_with_gates(workspace_root: Path) -> ProjectManager:
    return make_project_manager(workspace_root)


@pytest.fixture
def engine_with_gates(
    workspace_root: Path, project_manager_with_gates: ProjectManager
) -> PhaseStateEngine:
    return make_phase_state_engine(
        workspace_root,
        project_manager=project_manager_with_gates,
        workflow_gate_runner=_StaticGateRunner(blocking=("planning_deliverables",)),
    )


@pytest.fixture
def project_manager_no_gates(workspace_root_no_gates: Path) -> ProjectManager:
    return make_project_manager(workspace_root_no_gates)


@pytest.fixture
def engine_no_gates(
    workspace_root_no_gates: Path, project_manager_no_gates: ProjectManager
) -> PhaseStateEngine:
    return make_phase_state_engine(
        workspace_root_no_gates,
        project_manager=project_manager_no_gates,
        workflow_gate_runner=_StaticGateRunner(),
    )


# ---------------------------------------------------------------------------
# C3 — forced transition skipped-gate warning (GAP-03)
# ---------------------------------------------------------------------------


class TestForceTransitionSkippedGateWarning:
    """force_transition logs warning when it bypasses exit or entry gates (GAP-03)."""

    def test_force_transition_logs_warning_for_skipped_exit_gate(
        self,
        engine_with_gates: PhaseStateEngine,
        project_manager_with_gates: ProjectManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """force_transition logs warning when from_phase has exit_requires (GAP-03).

        Forcing planning → design bypasses the planning exit gate.
        Warning must mention skipped_gates.
        """
        project_manager_with_gates.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        engine_with_gates.initialize_branch(
            branch="feature/229-c3",
            issue_number=229,
            initial_phase="planning",
        )

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine_with_gates.force_transition(
                branch="feature/229-c3",
                to_phase="design",
                skip_reason="test: skip exit gate",
                human_approval_message="tester approved",
            )

        assert "skipped_gates" in caplog.text

    def test_force_transition_logs_warning_for_skipped_entry_expects(
        self,
        engine_with_gates: PhaseStateEngine,
        project_manager_with_gates: ProjectManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """force_transition logs warning when to_phase has entry_expects (GAP-03).

        Forcing research → implementation bypasses the implementation entry expects check.
        Warning must mention skipped_gates.
        """
        project_manager_with_gates.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        engine_with_gates.initialize_branch(
            branch="feature/229-c3b",
            issue_number=229,
            initial_phase="research",
        )

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine_with_gates.force_transition(
                branch="feature/229-c3b",
                to_phase="implementation",
                skip_reason="test: skip entry expects",
                human_approval_message="tester approved",
            )

        assert "skipped_gates" in caplog.text

    def test_force_transition_without_gates_logs_no_warning(
        self,
        engine_no_gates: PhaseStateEngine,
        project_manager_no_gates: ProjectManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """force_transition stays silent when neither phase has gates (GAP-03).

        Forcing research → planning when neither has exit_requires or entry_expects
        must not produce a skipped_gates warning.
        """
        project_manager_no_gates.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        engine_no_gates.initialize_branch(
            branch="feature/229-c3c",
            issue_number=229,
            initial_phase="research",
        )

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine_no_gates.force_transition(
                branch="feature/229-c3c",
                to_phase="planning",
                skip_reason="test: no gates present",
                human_approval_message="tester approved",
            )

        assert "skipped_gates" not in caplog.text


# ---------------------------------------------------------------------------
# C3 bugfix: warning must be silent when deliverables ARE present in deliverables.json
# ---------------------------------------------------------------------------


class TestForceTransitionNoWarningWhenDeliverablesPresent:
    """Warning must NOT fire when the gated deliverable key exists in deliverables.json.

    The original implementation warned based on config presence alone.
    The correct behaviour: only warn when the key is actually absent from deliverables.json.
    """

    def _setup(
        self, workspace_root: Path, initial_phase: str
    ) -> tuple[ProjectManager, PhaseStateEngine, str]:
        """Initialize project + branch and inject planning_deliverables directly."""
        pm = make_project_manager(workspace_root)
        pm.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        pm.save_planning_deliverables(
            229,
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

        engine = make_phase_state_engine(workspace_root, project_manager=pm)
        branch = "feature/229-bugfix"
        engine.initialize_branch(branch=branch, issue_number=229, initial_phase=initial_phase)
        return pm, engine, branch

    def test_force_transition_no_warning_when_exit_key_present(
        self,
        workspace_root: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No skipped_gates warning when exit_requires key exists in deliverables.json.

        Scenario: planning → design forced, planning_deliverables IS saved.
        Expected: transition succeeds silently (no ⚠️).
        """
        _, engine, branch = self._setup(workspace_root, initial_phase="planning")

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine.force_transition(
                branch=branch,
                to_phase="design",
                skip_reason="test: deliverables present",
                human_approval_message="tester approved",
            )

        assert "skipped_gates" not in caplog.text

    def test_force_transition_no_warning_when_entry_key_present(
        self,
        workspace_root: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No skipped_gates warning when entry_expects key exists in deliverables.json.

        Scenario: planning → implementation forced, planning_deliverables IS saved.
        Expected: transition succeeds silently (no ⚠️).
        """
        _, engine, branch = self._setup(workspace_root, initial_phase="planning")

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine.force_transition(
                branch=branch,
                to_phase="implementation",
                skip_reason="test: deliverables present, entry gate should be silent",
                human_approval_message="tester approved",
            )

        assert "skipped_gates" not in caplog.text
