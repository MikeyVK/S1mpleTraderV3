# mcp_server/config/schemas/contracts_config.py
# template=dto version=manual created=2026-05-02T00:00Z updated=
"""
Contracts config schema definitions.

Defines typed value objects for contracts.yaml (formerly phase_contracts.yaml).
Replaces PhaseContractsConfig with ContractsConfig, adding explicit workflow-phase
ordering via WorkflowEntry + WorkflowPhaseEntry (issue #271).

@layer: Backend (Config)
@dependencies: [pydantic, typing]
@responsibilities:
    - Define phase contract and check schema contracts
    - Provide ContractsConfig as single SSOT for workflow-phase membership and ordering
    - Expose get_first_phase, get_phases, validate_transition API
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BranchLocalArtifact(BaseModel):
    """Single branch-local artifact definition from merge_policy."""

    path: str
    reason: str


class MergePolicy(BaseModel):
    """Merge policy configuration from contracts.yaml."""

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


class PhaseInstructionsSpec(BaseModel):
    """Role-specific instructions for a workflow phase (frozen config value object).

    Sub-field of WorkflowPhaseEntry.instructions. Populated in contracts.yaml per
    workflow+phase combination. Stage 2 of issue #268.
    """

    model_config = ConfigDict(frozen=True)

    sub_role: str
    phase_instructions: str
    handover_template: str | None = None


class PhaseContractPhase(BaseModel):
    """Per-workflow phase contract entry. Frozen config value object (§5 CQS)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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


class WorkflowPhaseEntry(PhaseContractPhase):
    """Single phase entry in a workflow's ordered phase list.

    Extends PhaseContractPhase with a required name field. Inherits
    frozen=True and extra='forbid' from parent. The schema is generic:
    any phase name may be cycle_based — no fasename-checks on 'implementation'.
    """

    # inherits model_config = ConfigDict(extra="forbid", frozen=True) from PhaseContractPhase

    name: str = Field(..., description="Phase name; must exist in workphases.yaml catalog")
    instructions: PhaseInstructionsSpec


class WorkflowEntry(BaseModel):
    """Single workflow definition in contracts.yaml. Frozen config value object (§5 CQS)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    phases: list[WorkflowPhaseEntry] = Field(..., min_length=1)

    def get_phase_names(self) -> list[str]:
        return [p.name for p in self.phases]

    def get_phase(self, name: str) -> WorkflowPhaseEntry:
        for p in self.phases:
            if p.name == name:
                return p
        raise ValueError(f"Phase '{name}' not in workflow")


class ContractsConfig(BaseModel):
    """Typed root object for contracts.yaml. Frozen config value object (§5 CQS).

    Replaces PhaseContractsConfig. Provides explicit workflow-phase ordering
    and transition-validation API (get_first_phase, get_phases, validate_transition).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["1.0.0"] = Field("1.0.0", description="Config schema version")
    merge_policy: MergePolicy
    workflows: dict[str, WorkflowEntry] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_terminal_phase(self) -> ContractsConfig:
        terminal = self.merge_policy.pr_allowed_phase
        for name, workflow in self.workflows.items():
            last = workflow.phases[-1].name
            if last != terminal:
                raise ValueError(
                    f"Workflow '{name}': last phase must be '{terminal}' "
                    f"(merge_policy.pr_allowed_phase), got '{last}'"
                )
        return self

    def get_pr_allowed_phase(self) -> str:
        return self.merge_policy.pr_allowed_phase

    def get_first_phase(self, workflow_name: str) -> str:
        """Return the name of the first phase in the workflow.

        Raises ValueError if workflow_name is unknown.
        """
        return self._get_workflow(workflow_name).phases[0].name

    def get_phases(self, workflow_name: str) -> list[str]:
        """Return ordered list of phase names for the workflow.

        Raises ValueError if workflow_name is unknown.
        """
        return self._get_workflow(workflow_name).get_phase_names()

    def validate_transition(
        self,
        workflow_name: str,
        current_phase: str,
        target_phase: str,
    ) -> bool:
        """Validate sequential phase transition.

        Returns True on valid transition. Raises ValueError with descriptive
        message matching the current WorkflowConfig error contract on failure.
        """
        workflow = self._get_workflow(workflow_name)
        names = workflow.get_phase_names()
        if current_phase not in names:
            raise ValueError(
                f"Current phase '{current_phase}' not in workflow '{workflow_name}'\n"
                f"Valid phases: {names}"
            )
        if target_phase not in names:
            raise ValueError(
                f"Target phase '{target_phase}' not in workflow '{workflow_name}'\n"
                f"Valid phases: {names}"
            )
        current_idx = names.index(current_phase)
        target_idx = names.index(target_phase)
        if target_idx != current_idx + 1:
            next_phase = names[current_idx + 1] if current_idx + 1 < len(names) else None
            raise ValueError(
                f"Invalid transition: {current_phase} → {target_phase}\n"
                f"Expected next phase: {next_phase}\n"
                f"Workflow: {names}\n"
                "Hint: Use force_phase_transition tool for non-sequential transitions"
            )
        return True

    def _get_workflow(self, workflow_name: str) -> WorkflowEntry:
        if workflow_name not in self.workflows:
            available = ", ".join(sorted(self.workflows.keys()))
            raise ValueError(
                f"Unknown workflow: '{workflow_name}'\nAvailable workflows: {available}"
            )
        return self.workflows[workflow_name]
