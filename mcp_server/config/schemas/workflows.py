"""Pure WorkflowConfig schema for ConfigLoader-managed YAML loading."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WorkflowTemplate(BaseModel):
    """Single workflow definition."""

    name: str = Field(..., description="Workflow name")
    phases: list[str] = Field(..., min_length=1, description="Ordered list of phases")
    default_execution_mode: Literal["interactive", "autonomous"] = Field(
        default="interactive",
        description="Default execution mode for this workflow",
    )
    description: str = Field(default="", description="Human-readable workflow description")

    @model_validator(mode="after")
    def validate_phases(self) -> WorkflowTemplate:
        if len(self.phases) != len(set(self.phases)):
            raise ValueError(f"Duplicate phases in workflow '{self.name}': {self.phases}")
        if not all(phase.strip() for phase in self.phases):
            raise ValueError(f"Empty phase names in workflow '{self.name}'")
        return self


class WorkflowConfig(BaseModel):
    """Root workflow configuration value object."""

    version: str = Field(..., description="Config schema version")
    workflows: dict[str, WorkflowTemplate] = Field(..., description="Workflow definitions")

    def get_workflow(self, name: str) -> WorkflowTemplate:
        workflows_dict: dict[str, WorkflowTemplate] = dict(self.workflows)
        if name not in workflows_dict:
            available = ", ".join(sorted(workflows_dict.keys()))
            raise ValueError(
                f"Unknown workflow: '{name}'\n"
                f"Available workflows: {available}\n"
                "Hint: Add workflow definition to .st3/workflows.yaml"
            )
        return workflows_dict[name]

    def get_first_phase(self, workflow_name: str) -> str:
        return self.get_workflow(workflow_name).phases[0]

    def has_workflow(self, workflow_name: str) -> bool:
        return workflow_name in self.workflows

    def validate_transition(
        self,
        workflow_name: str,
        current_phase: str,
        target_phase: str,
    ) -> bool:
        workflow = self.get_workflow(workflow_name)

        if current_phase not in workflow.phases:
            raise ValueError(
                f"Current phase '{current_phase}' not in workflow '{workflow_name}'\n"
                f"Valid phases: {workflow.phases}"
            )

        if target_phase not in workflow.phases:
            raise ValueError(
                f"Target phase '{target_phase}' not in workflow '{workflow_name}'\n"
                f"Valid phases: {workflow.phases}"
            )

        current_idx = workflow.phases.index(current_phase)
        target_idx = workflow.phases.index(target_phase)
        if target_idx != current_idx + 1:
            next_phase = (
                workflow.phases[current_idx + 1] if current_idx + 1 < len(workflow.phases) else None
            )
            raise ValueError(
                f"Invalid transition: {current_phase} → {target_phase}\n"
                f"Expected next phase: {next_phase}\n"
                f"Workflow: {workflow.phases}\n"
                "Hint: Use force_phase_transition tool for non-sequential transitions"
            )

        return True
