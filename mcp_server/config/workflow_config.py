"""Workflow configuration model (Issue #149).

Purpose: Load workflows.yaml to resolve first workflow phase for phase:* label assembly.
Source: .st3/workflows.yaml
Pattern: Singleton with ClassVar (matches GitConfig pattern)
"""

from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel


class WorkflowEntry(BaseModel):
    """Single workflow definition from workflows.yaml."""

    name: str
    description: str = ""
    default_execution_mode: str = "interactive"
    phases: list[str]

    def first_phase(self) -> str:
        """Return the first phase of this workflow.

        Raises:
            ValueError: If the workflow has no phases.
        """
        if not self.phases:
            raise ValueError(f"Workflow '{self.name}' has no phases defined.")
        return self.phases[0]


class WorkflowConfig(BaseModel):
    """Workflow configuration loaded from workflows.yaml.

    Used to resolve the first phase of a workflow for `phase:*` label assembly.
    Singleton per process.
    """

    singleton_instance: ClassVar[Optional["WorkflowConfig"]] = None

    version: str
    phase_source: str = ""
    workflows: dict[str, WorkflowEntry]

    def get_first_phase(self, workflow_name: str) -> str:
        """Return the first phase for the given workflow name.

        Args:
            workflow_name: Workflow name (e.g. "feature", "hotfix").

        Returns:
            First phase string (e.g. "research", "tdd").

        Raises:
            ValueError: If the workflow is not defined in workflows.yaml.
        """
        entry = self.workflows.get(workflow_name)
        if entry is None:
            valid = sorted(self.workflows)
            raise ValueError(f"Unknown workflow: '{workflow_name}'. Valid workflows: {valid}")
        return entry.first_phase()

    def has_workflow(self, workflow_name: str) -> bool:
        """Return True if a workflow with the given name is defined."""
        return workflow_name in self.workflows

    @classmethod
    def from_file(cls, path: str = ".st3/workflows.yaml") -> "WorkflowConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            path: Path to workflows.yaml file.

        Returns:
            WorkflowConfig singleton instance.
        """
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        resolved = Path(path)
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))

        # workflows.yaml stores entries as dicts — normalise each into WorkflowEntry
        workflows_raw: dict = raw.get("workflows", {})
        workflows = {k: WorkflowEntry(**v) for k, v in workflows_raw.items()}

        instance = cls.model_validate(
            {
                "version": raw.get("version", "1.0"),
                "phase_source": raw.get("phase_source", ""),
                "workflows": workflows,
            }
        )
        cls.singleton_instance = instance
        return instance
