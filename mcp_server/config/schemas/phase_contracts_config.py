"""Pure phase contracts schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    exit_requires: list[CheckSpec] = Field(default_factory=list)
    cycle_exit_requires: dict[int, list[CheckSpec]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_cycle_based_commit_map(self) -> PhaseContractPhase:
        if self.cycle_based and not self.commit_type_map:
            raise ValueError("cycle_based phases require a non-empty commit_type_map")
        return self


class PhaseContractsConfig(BaseModel):
    """Typed root object for phase_contracts.yaml."""

    model_config = ConfigDict(extra="forbid")

    workflows: dict[str, dict[str, PhaseContractPhase]] = Field(default_factory=dict)
