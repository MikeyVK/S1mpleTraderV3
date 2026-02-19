"""Tests for PhaseStateEngine force_transition skipped-gate warning (Issue #229 Cycle 3).

GAP-03: Forced transitions bypass all hooks and deliverable checks with no warning.

C3 Deliverables:
  D3.1: force_transition logs warning listing skipped_gates when gates exist.
"""

import logging
from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Workspace root with workphases.yaml containing exit_requires + entry_expects."""
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
  tdd:
    display_name: "TDD"
    entry_expects:
      - key: "planning_deliverables"
        description: "Expected from planning"
  design:
    display_name: "Design"
  research:
    display_name: "Research"
"""
    )
    return tmp_path


@pytest.fixture
def workspace_root_no_gates(tmp_path: Path) -> Path:
    """Workspace root with workphases.yaml where phases have no gates."""
    st3 = tmp_path / ".st3"
    st3.mkdir()
    (st3 / "workphases.yaml").write_text(
        """
phases:
  research:
    display_name: "Research"
  planning:
    display_name: "Planning"
  design:
    display_name: "Design"
"""
    )
    return tmp_path


@pytest.fixture
def project_manager_with_gates(workspace_root: Path) -> ProjectManager:
    return ProjectManager(workspace_root=workspace_root)


@pytest.fixture
def engine_with_gates(
    workspace_root: Path, project_manager_with_gates: ProjectManager
) -> PhaseStateEngine:
    return PhaseStateEngine(
        workspace_root=workspace_root, project_manager=project_manager_with_gates
    )


@pytest.fixture
def project_manager_no_gates(workspace_root_no_gates: Path) -> ProjectManager:
    return ProjectManager(workspace_root=workspace_root_no_gates)


@pytest.fixture
def engine_no_gates(
    workspace_root_no_gates: Path, project_manager_no_gates: ProjectManager
) -> PhaseStateEngine:
    return PhaseStateEngine(
        workspace_root=workspace_root_no_gates, project_manager=project_manager_no_gates
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
                human_approval="tester approved",
            )

        assert "skipped_gates" in caplog.text

    def test_force_transition_logs_warning_for_skipped_entry_expects(
        self,
        engine_with_gates: PhaseStateEngine,
        project_manager_with_gates: ProjectManager,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """force_transition logs warning when to_phase has entry_expects (GAP-03).

        Forcing research → tdd bypasses the tdd entry expects check.
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
                to_phase="tdd",
                skip_reason="test: skip entry expects",
                human_approval="tester approved",
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
                human_approval="tester approved",
            )

        assert "skipped_gates" not in caplog.text


# ---------------------------------------------------------------------------
# C3 bugfix: warning must be silent when deliverables ARE present in projects.json
# ---------------------------------------------------------------------------


class TestForceTransitionNoWarningWhenDeliverablesPresent:
    """Warning must NOT fire when the gated deliverable key exists in projects.json (GAP-03 bugfix).

    The original implementation warned based on config presence alone.
    The correct behaviour: only warn when the key is actually absent from projects.json.
    """

    def _setup(self, workspace_root: Path, initial_phase: str) -> tuple[ProjectManager, PhaseStateEngine, str]:
        """Initialize project + branch and inject planning_deliverables directly."""
        pm = ProjectManager(workspace_root=workspace_root)
        pm.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        # Inject the key directly (bypasses schema validation — tests engine check logic only)
        import json as _json
        projects = _json.loads(pm.projects_file.read_text(encoding="utf-8"))
        projects["229"]["planning_deliverables"] = {"tdd_cycles": {"total": 1, "cycles": []}}
        pm.projects_file.write_text(_json.dumps(projects, indent=2))

        engine = PhaseStateEngine(workspace_root=workspace_root, project_manager=pm)
        branch = "feature/229-bugfix"
        engine.initialize_branch(branch=branch, issue_number=229, initial_phase=initial_phase)
        return pm, engine, branch

    def test_force_transition_no_warning_when_exit_key_present(
        self,
        workspace_root: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No skipped_gates warning when exit_requires key exists in projects.json.

        Scenario: planning → design forced, planning_deliverables IS saved.
        Expected: transition succeeds silently (no ⚠️).
        """
        _, engine, branch = self._setup(workspace_root, initial_phase="planning")

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine.force_transition(
                branch=branch,
                to_phase="design",
                skip_reason="test: deliverables present",
                human_approval="tester approved",
            )

        assert "skipped_gates" not in caplog.text

    def test_force_transition_no_warning_when_entry_key_present(
        self,
        workspace_root: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No skipped_gates warning when entry_expects key exists in projects.json.

        Scenario: planning → tdd forced, planning_deliverables IS saved.
        Expected: transition succeeds silently (no ⚠️).
        """
        _, engine, branch = self._setup(workspace_root, initial_phase="planning")

        with caplog.at_level(logging.WARNING, logger="mcp_server.managers.phase_state_engine"):
            engine.force_transition(
                branch=branch,
                to_phase="tdd",
                skip_reason="test: deliverables present, entry gate should be silent",
                human_approval="tester approved",
            )

        assert "skipped_gates" not in caplog.text
