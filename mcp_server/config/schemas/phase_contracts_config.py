# mcp_server/config/schemas/phase_contracts_config.py
"""
Phase contracts schema definitions.

Defines typed value objects for workflow phase contracts and cycle
requirements loaded by the config layer.

@layer: Backend (Config)
@dependencies: [pydantic, typing]
@responsibilities:
    - Define phase contract and check schema contracts
    - Validate workflow contract metadata structure
    - Represent cycle requirements for phase orchestration
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BranchLocalArtifact(BaseModel):
    """Single branch-local artifact definition from merge_policy."""

    path: str
    reason: str


class MergePolicy(BaseModel):
    """Merge policy configuration from phase_contracts.yaml."""

    pr_allowed_phase: str
    branch_local_artifacts: list[BranchLocalArtifact] = Field(default_factory=list)


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

    merge_policy: MergePolicy
    workflows: dict[str, dict[str, PhaseContractPhase]] = Field(default_factory=dict)

    def get_pr_allowed_phase(self) -> str:
        """Return the phase name that permits PR creation."""
        return self.merge_policy.pr_allowed_phase
