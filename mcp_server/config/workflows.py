"""Workflow configuration management (workflows.yaml).

This module provides Pydantic models for loading and validating workflow
configurations from .st3/workflows.yaml. Workflows define phase sequences
and execution modes for different issue types (feature, bug, hotfix, etc.).

Module Structure:
- WorkflowTemplate: Single workflow definition with phase validation
- WorkflowConfig: Root config model with workflow lookup and transition validation
- workflow_config: Module-level singleton (loaded at import)

Quality Requirements:
- Pylint: 10/10 (strict enforcement)
- Mypy: strict mode passing
- Coverage: 100% for all functions
"""
# pyright: reportAttributeAccessIssue=false

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class WorkflowTemplate(BaseModel):
    """Single workflow definition.

    Attributes:
        name: Workflow name (e.g., 'feature', 'hotfix')
        phases: Ordered list of phases (strict sequential transitions)
        default_execution_mode: Default execution mode (interactive or autonomous)
        description: Human-readable workflow description
    """

    name: str = Field(..., description="Workflow name (e.g., 'feature')")
    phases: list[str] = Field(
        ...,
        min_length=1,
        description="Ordered list of phases (strict sequential)"
    )
    default_execution_mode: Literal["interactive", "autonomous"] = Field(
        default="interactive",
        description="Default execution mode for this workflow"
    )
    description: str = Field(
        default="",
        description="Human-readable workflow description"
    )

    @model_validator(mode="after")
    def validate_phases(self) -> "WorkflowTemplate":
        """Ensure phases are unique and non-empty.

        Returns:
            Validated WorkflowTemplate instance

        Raises:
            ValueError: Duplicate phases or empty phase names detected
        """
        if len(self.phases) != len(set(self.phases)):
            raise ValueError(
                f"Duplicate phases in workflow '{self.name}': {self.phases}"
            )
        if not all(phase.strip() for phase in self.phases):
            raise ValueError(f"Empty phase names in workflow '{self.name}'")
        return self


class WorkflowConfig(BaseModel):
    """Root workflow configuration.

    Loaded from .st3/workflows.yaml at module import time. Provides workflow
    lookup and transition validation for phase state management.

    Attributes:
        version: Config schema version (e.g., '1.0')
        workflows: Workflow definitions by name
    """

    version: str = Field(..., description="Config schema version (e.g., '1.0')")
    workflows: dict[str, WorkflowTemplate] = Field(
        ...,
        description="Workflow definitions by name"
    )

    @classmethod
    def load(cls, path: Path | None = None) -> "WorkflowConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to workflows.yaml (default: .st3/workflows.yaml)

        Returns:
            Validated WorkflowConfig instance

        Raises:
            FileNotFoundError: Config file not found
            ValidationError: Invalid YAML structure
        """
        if path is None:
            path = Path(".st3/workflows.yaml")

        if not path.exists():
            raise FileNotFoundError(
                f"Workflow config not found: {path}\n"
                f"Expected location: .st3/workflows.yaml\n"
                f"Hint: Initialize workflows with default config"
            )

        with open(path, "r", encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)

        return cls(**data)

    def get_workflow(self, name: str) -> WorkflowTemplate:
        """Get workflow by name.

        Args:
            name: Workflow name (e.g., "feature")

        Returns:
            WorkflowTemplate instance

        Raises:
            ValueError: Unknown workflow name
        """
        workflows_dict: dict[str, WorkflowTemplate] = dict(self.workflows)
        if name not in workflows_dict:
            available = ", ".join(sorted(workflows_dict.keys()))
            raise ValueError(
                f"Unknown workflow: '{name}'\n"
                f"Available workflows: {available}\n"
                f"Hint: Add workflow definition to .st3/workflows.yaml"
            )
        return workflows_dict[name]

    def validate_transition(
        self,
        workflow_name: str,
        current_phase: str,
        target_phase: str
    ) -> bool:
        """Validate phase transition (strict sequential).

        Args:
            workflow_name: Workflow name
            current_phase: Current phase
            target_phase: Target phase

        Returns:
            True if transition is valid (next phase in sequence)

        Raises:
            ValueError: Invalid transition (not next phase)
        """
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

        # Strict sequential: target must be next phase
        if target_idx != current_idx + 1:
            next_phase = (
                workflow.phases[current_idx + 1]
                if current_idx + 1 < len(workflow.phases)
                else None
            )
            raise ValueError(
                f"Invalid transition: {current_phase} → {target_phase}\n"
                f"Expected next phase: {next_phase}\n"
                f"Workflow: {workflow.phases}\n"
                f"Hint: Use force_phase_transition tool for non-sequential transitions"
            )

        return True


# Module-level singleton (loaded at import time)
workflow_config = WorkflowConfig.load()
