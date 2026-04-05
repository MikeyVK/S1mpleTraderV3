# tests/mcp_server/unit/managers/test_phase_state_engine_c2.py
"""Tests for C_GATE_WIRING runtime gate ownership (Issue #257 Cycle 2).

Cycle 2 goals covered here:
- transition() blocks through WorkflowGateRunner.enforce().
- force_transition() reports blocked and passing gates through WorkflowGateRunner.inspect().
- PhaseContractResolver.resolve() is live on the transition path through phase_contracts.yaml.

These tests intentionally replace the old planning-hook assertions with behavioural
coverage on the real transition API. That carries the cycle-1 lesson forward:
prove runtime ownership through observable outcomes, not private seam inspection.

@layer: Tests (Unit)
@dependencies: [pytest, tests.mcp_server.test_support, mcp_server.managers.phase_state_engine]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.core.interfaces import GateReport, GateViolation
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import InMemoryStateRepository
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager


class BlockingGateRunner:
    """Behavioral fake that always blocks strict transitions."""

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        del workflow_name
        return phase == "implementation"

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        report = GateReport(
            passing=(),
            blocking=("research-doc",),
            details={"research-doc": "missing research document"},
        )
        raise GateViolation("missing research document", report)

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        return GateReport()


class InspectingGateRunner:
    """Behavioral fake that reports, but does not block, forced transitions."""

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        del workflow_name
        return phase == "implementation"

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        return GateReport()

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        return GateReport(
            passing=("design-doc",),
            blocking=("planning-doc",),
            details={"planning-doc": "missing planning document"},
        )


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace with hermetic workflow and phase-contract config."""
    config_dir = tmp_path / ".st3" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "workflows.yaml").write_text(
        """
version: "1.0"
workflows:
  feature:
    name: feature
    description: "Feature workflow"
    default_execution_mode: interactive
    phases:
      - research
      - planning
      - design
      - implementation
      - validation
      - documentation
""".strip(),
        encoding="utf-8",
    )
    (config_dir / "workphases.yaml").write_text(
        """
version: "1.0"
phases:
  research:
    display_name: "Research"
    subphases: []
  planning:
    display_name: "Planning"
    subphases: []
  design:
    display_name: "Design"
    subphases: []
  implementation:
    display_name: "Implementation"
    subphases: [red, green, refactor]
  validation:
    display_name: "Validation"
    subphases: []
  documentation:
    display_name: "Documentation"
    subphases: []
""".strip(),
        encoding="utf-8",
    )
    (config_dir / "phase_contracts.yaml").write_text(
        """
workflows:
  feature:
    research:
      exit_requires:
        - id: research-doc
          type: file_glob
          dir: docs/development
          pattern: issue*/research*.md
""".strip(),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def project_manager(workspace_root: Path) -> ProjectManager:
    """ProjectManager bound to the temp workspace."""
    return make_project_manager(workspace_root)


def test_transition_phase_raises_when_gate_blocks(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """transition() must fail when WorkflowGateRunner.enforce() blocks the boundary."""
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 2 strict gate test",
        workflow_name="feature",
    )
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=InMemoryStateRepository(),
        workflow_gate_runner=BlockingGateRunner(),
    )
    engine.initialize_branch(
        branch="feature/257-c2-blocking",
        issue_number=257,
        initial_phase="research",
    )

    with pytest.raises(GateViolation, match="missing research document"):
        engine.transition(branch="feature/257-c2-blocking", to_phase="planning")

    assert engine.get_current_phase("feature/257-c2-blocking") == "research"


def test_force_phase_transition_returns_gate_report_with_blocked_checks(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """force_transition() must surface inspect-mode gate results in its return payload."""
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 2 force inspection test",
        workflow_name="feature",
    )
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=InMemoryStateRepository(),
        workflow_gate_runner=InspectingGateRunner(),
    )
    engine.initialize_branch(
        branch="feature/257-c2-force",
        issue_number=257,
        initial_phase="planning",
    )

    result = engine.force_transition(
        branch="feature/257-c2-force",
        to_phase="design",
        skip_reason="audited bypass for test",
        human_approval="Verifier approved on 2026-04-04",
    )

    assert result["success"] is True
    assert result["skipped_gates"] == ["planning-doc"]
    assert result["passing_gates"] == ["design-doc"]
    assert result["gate_report"] == {
        "passing": ["design-doc"],
        "blocking": ["planning-doc"],
        "details": {"planning-doc": "missing planning document"},
    }


def test_transition_phase_enforces_contracts_from_phase_contracts_yaml(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """transition() must use phase_contracts.yaml through the live resolver path."""
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 2 live resolver test",
        workflow_name="feature",
    )
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=InMemoryStateRepository(),
    )
    branch = "feature/257-c2-live-resolver"
    engine.initialize_branch(branch=branch, issue_number=257, initial_phase="research")

    with pytest.raises(GateViolation) as exc_info:
        engine.transition(branch=branch, to_phase="planning")

    assert exc_info.value.report.blocking == ("research-doc",)

    research_dir = workspace_root / "docs" / "development" / "issue257"
    research_dir.mkdir(parents=True)
    (research_dir / "research_cycle2.md").write_text("# Research", encoding="utf-8")

    result = engine.transition(branch=branch, to_phase="planning")

    assert result == {"success": True, "from_phase": "research", "to_phase": "planning"}
