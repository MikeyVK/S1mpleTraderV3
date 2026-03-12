# mcp_server\managers\phase_contract_resolver.py
# template=generic version=f35abd82 created=2026-03-12T21:30Z updated=
"""Phase contract configuration loading and resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from mcp_server.config.workphases_config import WorkphasesConfig
from mcp_server.core.exceptions import ConfigError

_PHASE_CONTRACTS_DISPLAY_PATH = ".st3/config/phase_contracts.yaml"
_WORKPHASES_DISPLAY_PATH = ".st3/workphases.yaml"


class CheckSpec(BaseModel):
    """Typed phase check specification loaded from YAML."""

    id: str
    type: str
    required: bool = True
    file: str | None = None
    heading: str | None = None


class PhaseContractPhase(BaseModel):
    """Per-workflow phase contract entry."""

    subphases: list[str] = Field(default_factory=list)
    commit_type_map: dict[str, str] = Field(default_factory=dict)
    cycle_based: bool = False
    checks: list[CheckSpec] = Field(default_factory=list)
    cycle_checks: dict[int, list[CheckSpec]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_cycle_based_commit_map(self) -> PhaseContractPhase:
        """Reject cycle-based phases without commit type mapping."""
        if self.cycle_based and not self.commit_type_map:
            raise ValueError("cycle_based phases require a non-empty commit_type_map")
        return self


class PhaseContractsConfig(BaseModel):
    """Typed root object for phase_contracts.yaml."""

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
    """Facade bundling workphase and phase contract configuration."""

    workphases: WorkphasesConfig
    phase_contracts: PhaseContractsConfig

    @classmethod
    def from_workspace(cls, workspace_root: Path | str) -> PhaseConfigContext:
        """Load both config sources from a workspace root."""
        root = Path(workspace_root)
        workphases = WorkphasesConfig(root / _WORKPHASES_DISPLAY_PATH)
        phase_contracts = PhaseContractsConfig.from_file(
            root / _PHASE_CONTRACTS_DISPLAY_PATH,
            display_path=_PHASE_CONTRACTS_DISPLAY_PATH,
        )
        return cls(workphases=workphases, phase_contracts=phase_contracts)


class PhaseContractResolver:
    """Resolve workflow-phase contracts into concrete check specs."""

    def __init__(self, config: PhaseConfigContext) -> None:
        self._config = config

    def resolve(self, workflow_name: str, phase: str, cycle_number: int | None) -> list[CheckSpec]:
        """Resolve phase and cycle-specific checks for the requested workflow."""
        workflow_contracts = self._config.phase_contracts.workflows.get(workflow_name)
        if workflow_contracts is None:
            return []

        phase_contract = workflow_contracts.get(phase)
        if phase_contract is None:
            return []

        resolved_checks = list(phase_contract.checks)
        if cycle_number is not None:
            resolved_checks.extend(phase_contract.cycle_checks.get(cycle_number, []))
        return resolved_checks
