# tests\mcp_server\unit\managers\test_consumers_c4.py
# template=unit_test version=3d15d309 created=2026-05-02T19:05Z updated=
"""
Unit tests for C4: runtime consumer migration to ContractsConfig.

Covers PhaseStateEngine, ProjectManager, and CreateIssueTool constructor
signature verification and key behavioral delegation via ContractsConfig.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.managers.phase_state_engine,
    mcp_server.managers.project_manager, mcp_server.tools.issue_tools]
@responsibilities:
    - PhaseStateEngine accepts contracts_config: ContractsConfig; workflow_config param removed
    - PhaseStateEngine.transition uses contracts_config.validate_transition
    - ProjectManager accepts contracts_config: ContractsConfig; workflow_config param removed
    - ProjectManager.initialize_project persists required_phases from contracts_config.get_phases
    - CreateIssueTool accepts contracts_config: ContractsConfig; workflow_config param removed
    - CreateIssueTool._assemble_labels derives first phase from contracts_config.get_first_phase
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.config.schemas.contracts_config import (
    BranchLocalArtifact,
    ContractsConfig,
    MergePolicy,
    PhaseInstructionsSpec,
    WorkflowEntry,
    WorkflowPhaseEntry,
)
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.issue_tools import CreateIssueTool
from tests.mcp_server.test_support import get_default_server_root

_STUB_INSTRUCTIONS = PhaseInstructionsSpec(
    sub_role="test-role",
    phase_instructions="Test instructions.",
    handover_template="Test handover.",
)


def _minimal_contracts(first_phase: str = "research") -> ContractsConfig:
    return ContractsConfig(
        merge_policy=MergePolicy(
            pr_allowed_phase="ready",
            branch_local_artifacts=[
                BranchLocalArtifact(
                    path=f"{get_default_server_root()}/state.json", reason="branch-local"
                )
            ],
        ),
        workflows={
            "feature": WorkflowEntry(
                phases=[
                    WorkflowPhaseEntry(name=first_phase, instructions=_STUB_INSTRUCTIONS),
                    WorkflowPhaseEntry(name="design", instructions=_STUB_INSTRUCTIONS),
                    WorkflowPhaseEntry(name="ready", instructions=_STUB_INSTRUCTIONS),
                ]
            )
        },
    )


# ---------------------------------------------------------------------------
# PhaseStateEngine — constructor signature
# ---------------------------------------------------------------------------


class TestPhaseStateEngineConstructorC4:
    def test_accepts_contracts_config_parameter(self) -> None:
        """PhaseStateEngine.__init__ must have contracts_config parameter."""
        sig = inspect.signature(PhaseStateEngine.__init__)
        assert "contracts_config" in sig.parameters

    def test_does_not_accept_workflow_config_parameter(self) -> None:
        """PhaseStateEngine.__init__ must NOT have workflow_config parameter."""
        sig = inspect.signature(PhaseStateEngine.__init__)
        assert "workflow_config" not in sig.parameters


class TestPhaseStateEngineTransitionC4:
    def _build_engine(self, tmp_path: Path, contracts: ContractsConfig) -> PhaseStateEngine:
        """Build a minimal PhaseStateEngine with injected contracts_config."""
        from mcp_server.schemas import GitConfig  # noqa: PLC0415

        git_config = MagicMock(spec=GitConfig)
        project_manager = MagicMock()
        state_repository = MagicMock()
        scope_decoder = MagicMock()
        workflow_gate_runner = MagicMock()
        workflow_gate_runner.enforce_phase_exit = MagicMock(return_value=None)
        workflow_state_mutator = MagicMock()

        return PhaseStateEngine(
            workspace_root=tmp_path,
            project_manager=project_manager,
            git_config=git_config,
            contracts_config=contracts,
            state_repository=state_repository,
            scope_decoder=scope_decoder,
            workflow_gate_runner=workflow_gate_runner,
            workflow_state_mutator=workflow_state_mutator,
            server_root=tmp_path / get_default_server_root(),
        )

    def test_validate_transition_value_error_propagates(self, tmp_path: Path) -> None:
        """ValueError from contracts_config.validate_transition must propagate to caller."""
        contracts = _minimal_contracts()
        engine = self._build_engine(tmp_path, contracts)

        mock_contracts = MagicMock(spec=ContractsConfig)
        mock_contracts.validate_transition.side_effect = ValueError("invalid transition")
        # test-only: inject mock to verify validate_transition error propagation
        engine._contracts_config = mock_contracts  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

        state = MagicMock()
        state.branch = "feature/1-test"
        state.current_phase = "research"
        state.workflow_name = "feature"
        state.issue_number = 1
        state.current_cycle = None
        # test-only: configure state repository mock for transition path
        engine._state_repository.load.return_value = state  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]

        with pytest.raises(ValueError, match="invalid transition"):
            engine.transition("feature/1-test", to_phase="design")


# ---------------------------------------------------------------------------
# ProjectManager — constructor + phase delegation
# ---------------------------------------------------------------------------


class TestProjectManagerConstructorC4:
    def test_accepts_contracts_config_parameter(self) -> None:
        """ProjectManager.__init__ must have contracts_config parameter."""
        sig = inspect.signature(ProjectManager.__init__)
        assert "contracts_config" in sig.parameters

    def test_does_not_accept_workflow_config_parameter(self) -> None:
        """ProjectManager.__init__ must NOT have workflow_config parameter."""
        sig = inspect.signature(ProjectManager.__init__)
        assert "workflow_config" not in sig.parameters


class TestProjectManagerPhaseDelegationC4:
    def _build_pm(self, tmp_path: Path, contracts: ContractsConfig) -> ProjectManager:
        return ProjectManager(
            workspace_root=tmp_path,
            contracts_config=contracts,
            workflow_status_resolver=MagicMock(),
            server_root=tmp_path / get_default_server_root(),
        )

    def test_get_first_phase_returns_research_for_feature(self, tmp_path: Path) -> None:
        """ProjectManager.get_first_phase must delegate to contracts_config."""
        pm = self._build_pm(tmp_path, _minimal_contracts(first_phase="research"))
        assert pm.get_first_phase("feature") == "research"

    def test_get_phases_returns_ordered_sequence_for_feature(self, tmp_path: Path) -> None:
        """ProjectManager.get_phases must delegate to contracts_config."""
        pm = self._build_pm(tmp_path, _minimal_contracts())
        assert pm.get_phases("feature") == ["research", "design", "ready"]

    def test_create_project_plan_stores_required_phases_from_contracts(
        self, tmp_path: Path
    ) -> None:
        """initialize_project must persist required_phases from contracts_config.get_phases."""
        (tmp_path / get_default_server_root()).mkdir(parents=True)
        pm = self._build_pm(tmp_path, _minimal_contracts())
        pm.initialize_project(
            issue_number=1,
            issue_title="Test Issue",
            workflow_name="feature",
        )
        deliverables_file = tmp_path / get_default_server_root() / "deliverables.json"
        assert deliverables_file.exists()
        data = json.loads(deliverables_file.read_text(encoding="utf-8"))
        projects = data.get("projects", data)
        assert projects["1"]["required_phases"] == ["research", "design", "ready"]


# ---------------------------------------------------------------------------
# CreateIssueTool — constructor + first-phase derivation
# ---------------------------------------------------------------------------


class TestCreateIssueToolConstructorC4:
    def test_accepts_contracts_config_parameter(self) -> None:
        """CreateIssueTool.__init__ must have contracts_config parameter."""
        sig = inspect.signature(CreateIssueTool.__init__)
        assert "contracts_config" in sig.parameters

    def test_does_not_accept_workflow_config_parameter(self) -> None:
        """CreateIssueTool.__init__ must NOT have workflow_config parameter."""
        sig = inspect.signature(CreateIssueTool.__init__)
        assert "workflow_config" not in sig.parameters


class TestCreateIssueToolFirstPhaseC4:
    def test_assemble_labels_derives_first_phase_from_contracts(self) -> None:
        """_assemble_labels must derive first phase via contracts_config.get_first_phase."""
        from mcp_server.config.schemas.issue_config import IssueConfig  # noqa: PLC0415
        from mcp_server.config.schemas.milestone_config import MilestoneConfig  # noqa: PLC0415
        from mcp_server.tools.issue_tools import CreateIssueInput  # noqa: PLC0415

        issue_config = MagicMock(spec=IssueConfig)
        issue_config.get_label.return_value = "type:feature"
        issue_config.get_workflow.return_value = "feature"

        tool = CreateIssueTool(
            manager=MagicMock(),
            issue_config=issue_config,
            milestone_config=MagicMock(spec=MilestoneConfig),
            contracts_config=_minimal_contracts(first_phase="research"),
            label_config=None,
            scope_config=None,
            git_config=None,
        )
        params = MagicMock(spec=CreateIssueInput)
        params.is_epic = False
        params.issue_type = "feature"
        params.scope = "mcp-server"
        params.priority = "high"
        params.parent_issue = None

        # test-only: verify protected method derives phase from contracts_config
        labels = tool._assemble_labels(params)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        assert "phase:research" in labels
