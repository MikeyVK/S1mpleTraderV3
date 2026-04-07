"""Phase contract configuration loading and resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_server.core.exceptions import ConfigError
from mcp_server.schemas import CheckSpec, PhaseContractsConfig, WorkphasesConfig

_PHASE_CONTRACTS_DISPLAY_PATH = ".st3/config/phase_contracts.yaml"
_WORKPHASES_DISPLAY_PATH = ".st3/config/workphases.yaml"
_DELIVERABLES_DISPLAY_PATH = ".st3/deliverables.json"


@dataclass(frozen=True)
class PhaseConfigContext:
    """Facade bundling workphase, phase contract, and issue deliverable context."""

    workphases: WorkphasesConfig
    phase_contracts: PhaseContractsConfig
    planning_deliverables: dict[str, Any] | None = None

    @staticmethod
    def _load_planning_deliverables(
        workspace_root: Path,
        issue_number: int | None,
    ) -> dict[str, Any] | None:
        """Load planning deliverables for one issue from deliverables.json."""
        if issue_number is None:
            return None

        deliverables_path = workspace_root / _DELIVERABLES_DISPLAY_PATH
        if not deliverables_path.exists():
            return None

        data = json.loads(deliverables_path.read_text(encoding="utf-8-sig"))
        issue_data = data.get(str(issue_number), {})
        planning_deliverables = issue_data.get("planning_deliverables")
        return planning_deliverables if isinstance(planning_deliverables, dict) else None


class PhaseContractResolver:
    """Resolve workflow-phase contracts into concrete check specs."""

    def __init__(self, config: PhaseConfigContext) -> None:
        self._config = config

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        """Report whether one workflow phase is marked cycle_based in config."""
        workflow_contracts = self._config.phase_contracts.workflows.get(workflow_name)
        if workflow_contracts is None:
            return False

        phase_contract = workflow_contracts.get(phase)
        if phase_contract is None:
            return False

        return phase_contract.cycle_based

    def resolve_commit_type(
        self,
        workflow_name: str,
        phase: str,
        sub_phase: str | None,
    ) -> str | None:
        """Resolve commit type from phase contracts for one workflow phase."""
        workflow_contracts = self._config.phase_contracts.workflows.get(workflow_name)
        if workflow_contracts is None:
            return None

        phase_contract = workflow_contracts.get(phase)
        if phase_contract is None or sub_phase is None:
            return None

        if sub_phase not in phase_contract.commit_type_map:
            raise ConfigError(
                (
                    f"Missing commit_type_map entry for sub_phase '{sub_phase}' "
                    f"in workflow '{workflow_name}' phase '{phase}'"
                ),
                file_path=_PHASE_CONTRACTS_DISPLAY_PATH,
            )

        return phase_contract.commit_type_map[sub_phase]

    def resolve(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None,
    ) -> list[CheckSpec]:
        """Resolve phase and cycle-specific checks for the requested workflow.

        A6 merge semantics:
        - required config gates are immutable
        - issue-specific gates may override recommended config gates by matching id
        - issue-specific gates may extend the resolved set with new recommended checks
        """
        workflow_contracts = self._config.phase_contracts.workflows.get(workflow_name)
        if workflow_contracts is None:
            return []

        phase_contract = workflow_contracts.get(phase)
        if phase_contract is None:
            return []

        config_checks = [*phase_contract.exit_requires]
        if cycle_number is not None:
            config_checks.extend(phase_contract.cycle_exit_requires.get(cycle_number, []))

        issue_checks = self._resolve_issue_checks(
            workflow_name=workflow_name,
            phase=phase,
            cycle_number=cycle_number,
        )
        return self._merge_checks(config_checks=config_checks, issue_checks=issue_checks)

    def _resolve_issue_checks(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None,
    ) -> list[CheckSpec]:
        """Resolve issue-specific checks from deliverables.json for the active phase."""
        planning_deliverables = self._config.planning_deliverables
        if planning_deliverables is None:
            return []

        deliverables: list[dict[str, Any]] = []
        if self.is_cycle_based_phase(workflow_name, phase) and cycle_number is not None:
            tdd_cycles = planning_deliverables.get("tdd_cycles", {})
            cycles = tdd_cycles.get("cycles", [])
            matching_cycle = next(
                (
                    cycle
                    for cycle in cycles
                    if isinstance(cycle, dict) and cycle.get("cycle_number") == cycle_number
                ),
                None,
            )
            if isinstance(matching_cycle, dict):
                deliverables = matching_cycle.get("deliverables", [])
        else:
            phase_data = planning_deliverables.get(phase, {})
            if isinstance(phase_data, dict):
                deliverables = phase_data.get("deliverables", [])

        resolved_issue_checks: list[CheckSpec] = []
        for deliverable in deliverables:
            if not isinstance(deliverable, dict):
                continue
            validates = deliverable.get("validates")
            if not isinstance(validates, dict):
                continue
            issue_check_payload = {
                "id": str(deliverable.get("id", "issue-check")),
                "required": False,
                **validates,
            }
            resolved_issue_checks.append(CheckSpec.model_validate(issue_check_payload))

        return resolved_issue_checks

    def _merge_checks(
        self,
        config_checks: list[CheckSpec],
        issue_checks: list[CheckSpec],
    ) -> list[CheckSpec]:
        """Apply A6 merge semantics for config and issue-specific gates."""
        required_checks = [check for check in config_checks if check.required]
        required_ids = {check.id for check in required_checks}

        recommended_checks = [check for check in config_checks if not check.required]
        merged_recommended: dict[str, CheckSpec] = {check.id: check for check in recommended_checks}
        recommended_order = [check.id for check in recommended_checks]

        for issue_check in issue_checks:
            if issue_check.id in required_ids:
                continue
            if issue_check.id not in merged_recommended:
                recommended_order.append(issue_check.id)
            merged_recommended[issue_check.id] = issue_check

        return [
            *required_checks,
            *(merged_recommended[check_id] for check_id in recommended_order),
        ]
