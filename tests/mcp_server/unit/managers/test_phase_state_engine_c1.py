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
from mcp_server.schemas import CheckSpec


class FakeGateRunner:
    """Minimal workflow gate runner test double."""

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
        return GateReport()


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace with minimal local config for gate-runner tests."""
    config_dir = tmp_path / ".st3" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "workphases.yaml").write_text(
        """
version: "1"
phases:
  implementation:
    display_name: "Implementation"
    subphases: [red, green, refactor]
""".strip(),
        encoding="utf-8",
    )
    (config_dir / "phase_contracts.yaml").write_text(
        """
workflows:
  feature:
    implementation:
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
""".strip(),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def repo_loader() -> ConfigLoader:
    """Repository config loader for shared workflow/git config."""
    return ConfigLoader(Path(".st3/config"))


@pytest.fixture
def workspace_loader(workspace_root: Path) -> ConfigLoader:
    """Workspace-local config loader for hermetic gate-runner tests."""
    return ConfigLoader(workspace_root / ".st3" / "config")


@pytest.fixture
def project_manager(workspace_root: Path, repo_loader: ConfigLoader) -> ProjectManager:
    """ProjectManager bound to the temp workspace."""
    return ProjectManager(
        workspace_root=workspace_root,
        workflow_config=repo_loader.load_workflow_config(),
    )


def _make_runner(workspace_root: Path, workspace_loader: ConfigLoader) -> WorkflowGateRunner:
    """Create a real WorkflowGateRunner backed by local phase_contracts.yaml."""
    resolver = PhaseContractResolver(
        PhaseConfigContext(
            workphases=workspace_loader.load_workphases_config(),
            phase_contracts=workspace_loader.load_phase_contracts_config(),
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
    """WorkflowGateRunner returns GateReport for both enforce and inspect modes."""
    matching_dir = workspace_root / "docs" / "development" / "issue257"
    matching_dir.mkdir(parents=True)
    (matching_dir / "research_cycle1.md").write_text("cycle 1", encoding="utf-8")

    runner = _make_runner(workspace_root, workspace_loader)

    enforce_report = runner.enforce(workflow_name="feature", phase="implementation", cycle_number=1)
    inspect_report = runner.inspect(workflow_name="feature", phase="implementation", cycle_number=1)

    assert enforce_report == GateReport(passing=("cycle-docs",), blocking=(), details={})
    assert inspect_report == GateReport(passing=("cycle-docs",), blocking=(), details={})


def test_workflow_gate_runner_enforce_raises_when_resolved_file_glob_matches_no_files(
    workspace_root: Path,
    workspace_loader: ConfigLoader,
) -> None:
    """WorkflowGateRunner raises when a resolved file_glob check finds no matching files."""
    runner = _make_runner(workspace_root, workspace_loader)

    with pytest.raises(GateViolation) as exc_info:
        runner.enforce(workflow_name="feature", phase="implementation", cycle_number=1)

    report = exc_info.value.report
    assert report.passing == ()
    assert report.blocking == ("cycle-docs",)
    assert "cycle-docs" in report.details


def test_workflow_gate_runner_enforce_reports_all_blocking_checks(
    workspace_root: Path,
    workspace_loader: ConfigLoader,
) -> None:
    """enforce() raises with a complete GateReport when multiple checks block."""
    runner = _make_runner(workspace_root, workspace_loader)
    checks = [
        CheckSpec.model_validate(
            {
                "id": "missing-a",
                "type": "file_glob",
                "dir": "docs/development",
                "pattern": "issue*/missing_a_*.md",
            }
        ),
        CheckSpec.model_validate(
            {
                "id": "missing-b",
                "type": "file_glob",
                "dir": "docs/development",
                "pattern": "issue*/missing_b_*.md",
            }
        ),
    ]

    with pytest.raises(GateViolation) as exc_info:
        runner.enforce(
            workflow_name="feature",
            phase="implementation",
            cycle_number=1,
            checks=checks,
        )

    report = exc_info.value.report
    assert report.passing == ()
    assert report.blocking == ("missing-a", "missing-b")
    assert set(report.details) == {"missing-a", "missing-b"}
