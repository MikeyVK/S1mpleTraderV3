# mcp_server\managers\phase_contract_resolver.py
# template=generic version=f35abd82 created=2026-03-12T21:30Z updated=
"""Phase contract configuration loading and resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator

from mcp_server.config.workphases_config import WorkphasesConfig
from mcp_server.core.exceptions import ConfigError

_PHASE_CONTRACTS_DISPLAY_PATH = ".st3/config/phase_contracts.yaml"
_WORKPHASES_DISPLAY_PATH = ".st3/workphases.yaml"
_DELIVERABLES_DISPLAY_PATH = ".st3/deliverables.json"


class CheckSpec(BaseModel):
    """Typed phase check specification loaded from YAML or deliverables.json."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    required: bool = True
    file: str | None = None
    heading: str | None = None
    text: str | None = None
    dir: str | None = None
    pattern: str | None = None
    path: str | None = None


class PhaseContractPhase(BaseModel):
    """Per-workflow phase contract entry."""

    subphases: list[str] = Field(default_factory=list)
    commit_type_map: dict[str, str] = Field(default_factory=dict)
    cycle_based: bool = False
    exit_requires: list[CheckSpec] = Field(
        default_factory=list,
        validation_alias=AliasChoices("exit_requires", "checks"),
    )
    cycle_exit_requires: dict[int, list[CheckSpec]] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("cycle_exit_requires", "cycle_checks"),
    )

    @model_validator(mode="after")
    def validate_cycle_based_commit_map(self) -> PhaseContractPhase:
        """Reject cycle-based phases without commit type mapping."""
        if self.cycle_based and not self.commit_type_map:
            raise ValueError("cycle_based phases require a non-empty commit_type_map")
        return self


class PhaseContractsConfig(BaseModel):
    """Typed root object for phase_contracts.yaml."""

    model_config = ConfigDict(extra="forbid")

    workflows: dict[str, dict[str, PhaseContractPhase]] = Field(default_factory=dict)

    @classmethod
    def from_file(
        cls,
        file_path: Path | str,
        display_path: str = _PHASE_CONTRACTS_DISPLAY_PATH,
    ) -> PhaseContractsConfig:
        """Load and validate phase contracts from YAML."""
        path = Path(file_path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {display_path}", file_path=display_path)

        try:
            with path.open(encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"Invalid YAML in {display_path}: {exc}",
                file_path=display_path,
            ) from exc

        if "workflows" not in data:
            raise ConfigError(
                f"Missing 'workflows' key in {display_path}",
                file_path=display_path,
            )

        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ConfigError(
                f"Config validation failed for {display_path}: {exc}",
                file_path=display_path,
            ) from exc


@dataclass(frozen=True)
class PhaseConfigContext:
    """Facade bundling workphase, phase contract, and issue deliverable context."""

    workphases: WorkphasesConfig
    phase_contracts: PhaseContractsConfig
    planning_deliverables: dict[str, Any] | None = None

    @classmethod
    def from_workspace(
        cls, workspace_root: Path | str, issue_number: int | None = None
    ) -> PhaseConfigContext:
        """Load config sources from a workspace root.

        If issue_number is provided, include issue-specific planning deliverables
        from deliverables.json so A6 merge semantics can be resolved in one place.
        """
        root = Path(workspace_root)
        workphases = WorkphasesConfig(root / _WORKPHASES_DISPLAY_PATH)
        phase_contracts = PhaseContractsConfig.from_file(
            root / _PHASE_CONTRACTS_DISPLAY_PATH,
            display_path=_PHASE_CONTRACTS_DISPLAY_PATH,
        )
        planning_deliverables = cls._load_planning_deliverables(root, issue_number)
        return cls(
            workphases=workphases,
            phase_contracts=phase_contracts,
            planning_deliverables=planning_deliverables,
        )

    @staticmethod
    def _load_planning_deliverables(
        workspace_root: Path, issue_number: int | None
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

    def resolve(self, workflow_name: str, phase: str, cycle_number: int | None) -> list[CheckSpec]:
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

        issue_checks = self._resolve_issue_checks(phase=phase, cycle_number=cycle_number)
        return self._merge_checks(config_checks=config_checks, issue_checks=issue_checks)

    def _resolve_issue_checks(self, phase: str, cycle_number: int | None) -> list[CheckSpec]:
        """Resolve issue-specific checks from deliverables.json for the active phase."""
        planning_deliverables = self._config.planning_deliverables
        if planning_deliverables is None:
            return []

        deliverables: list[dict[str, Any]] = []
        if phase == "implementation" and cycle_number is not None:
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
        self, config_checks: list[CheckSpec], issue_checks: list[CheckSpec]
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

        return [*required_checks, *(merged_recommended[check_id] for check_id in recommended_order)]
