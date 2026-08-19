"""Tests for C_GATE_API seams and WorkflowGateRunner behavior (Issue #257 Cycle 1).

Cycle 1 goals covered here:
- WorkflowGateRunner exposes enforce and inspect modes.
- WorkflowGateRunner bridges resolved file_glob CheckSpec objects into DeliverableChecker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.interfaces import GateReport, GateViolation
from mcp_server.managers.deliverable_checker import DeliverableChecker
from mcp_server.managers.phase_contract_resolver import (
    PhaseConfigContext,
    PhaseContractResolver,
)
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.workflow_gate_runner import WorkflowGateRunner
from tests.mcp_server.test_support import get_default_server_root, make_project_manager


class FakeGateRunner:
    """Minimal workflow gate runner test double."""

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        del workflow_name
        return phase == "implementation"

    def enforce_phase_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()

    def inspect_phase_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()

    def enforce_cycle_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()

    def inspect_cycle_exit(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int,
    ) -> GateReport:
        del workflow_name, phase, cycle_number
        return GateReport()


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace with minimal local config for gate-runner tests."""
    config_dir = tmp_path / get_default_server_root() / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "workphases.yaml").write_text(
        """
version: "1.0.0"
phases:
  implementation:
    display_name: "Implementation"
    subphases: [red, green, refactor]
  ready:
    display_name: "Ready"
    terminal: true
""".strip(),
        encoding="utf-8",
    )
    (config_dir / "contracts.yaml").write_text(
        """
version: "1.0.0"
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
workflows:
  feature:
    phases:
      - name: implementation
        cycle_based: true
        subphases: [red, green, refactor]
        commit_type_map:
          red: test
          green: feat
          refactor: refactor
        cycle_exit_requires:
          1:
            - id: cycle-docs
              type: file_glob
              dir: docs/development
              pattern: issue*/research_*.md
            - id: cycle-docs-b
              type: file_glob
              dir: docs/development
              pattern: issue*/missing_b_*.md
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
      - name: ready
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
""".strip(),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def repo_loader() -> ConfigLoader:
    """Repository config loader for shared workflow/git config."""
    return ConfigLoader(Path(f"{get_default_server_root()}/config"))


@pytest.fixture
def workspace_loader(workspace_root: Path) -> ConfigLoader:
    """Workspace-local config loader for hermetic gate-runner tests."""
    return ConfigLoader(workspace_root / get_default_server_root() / "config")


@pytest.fixture
def project_manager(workspace_root: Path, repo_loader: ConfigLoader) -> ProjectManager:  # noqa: ARG001
    """ProjectManager bound to the temp workspace."""
    return make_project_manager(
        workspace_root=workspace_root,
    )


def _make_runner(workspace_root: Path, workspace_loader: ConfigLoader) -> WorkflowGateRunner:
    """Create a real WorkflowGateRunner backed by local contracts.yaml."""
    resolver = PhaseContractResolver(
        PhaseConfigContext(
            workphases=workspace_loader.load_workphases_config(),
            contracts=workspace_loader.load_contracts_config(),
        )
    )
    return WorkflowGateRunner(
        deliverable_checker=DeliverableChecker(workspace_root),
        phase_contract_resolver=resolver,
    )


def test_workflow_gate_runner_exposes_enforce_and_inspect_modes(
    workspace_root: Path,
    workspace_loader: ConfigLoader,
) -> None:
    """WorkflowGateRunner returns GateReport for both enforce_cycle_exit and inspect_cycle_exit."""
    matching_dir = workspace_root / "docs" / "development" / "issue257"
    matching_dir.mkdir(parents=True)
    (matching_dir / "research_cycle1.md").write_text("cycle 1", encoding="utf-8")
    (matching_dir / "missing_b_cycle1.md").write_text("cycle 1 b", encoding="utf-8")

    runner = _make_runner(workspace_root, workspace_loader)

    enforce_report = runner.enforce_cycle_exit(
        workflow_name="feature", phase="implementation", cycle_number=1
    )
    inspect_report = runner.inspect_cycle_exit(
        workflow_name="feature", phase="implementation", cycle_number=1
    )

    assert enforce_report == GateReport(
        passing=("cycle-docs", "cycle-docs-b"), blocking=(), details={}
    )
    assert inspect_report == GateReport(
        passing=("cycle-docs", "cycle-docs-b"), blocking=(), details={}
    )


def test_workflow_gate_runner_enforce_cycle_exit_raises_when_no_files_match(
    workspace_root: Path,
    workspace_loader: ConfigLoader,
) -> None:
    """WorkflowGateRunner raises when resolved file_glob checks find no matching files."""
    runner = _make_runner(workspace_root, workspace_loader)

    with pytest.raises(GateViolation) as exc_info:
        runner.enforce_cycle_exit(workflow_name="feature", phase="implementation", cycle_number=1)

    report = exc_info.value.report
    assert report.passing == ()
    assert report.blocking == ("cycle-docs", "cycle-docs-b")
    assert "cycle-docs" in report.details
    assert "cycle-docs-b" in report.details


def test_workflow_gate_runner_enforce_cycle_exit_reports_all_blocking_checks(
    workspace_root: Path,
    workspace_loader: ConfigLoader,
) -> None:
    """enforce_cycle_exit() raises with a complete GateReport when multiple checks block."""
    runner = _make_runner(workspace_root, workspace_loader)

    with pytest.raises(GateViolation) as exc_info:
        runner.enforce_cycle_exit(workflow_name="feature", phase="implementation", cycle_number=1)

    report = exc_info.value.report
    assert report.passing == ()
    assert report.blocking == ("cycle-docs", "cycle-docs-b")
    assert set(report.details) == {"cycle-docs", "cycle-docs-b"}
