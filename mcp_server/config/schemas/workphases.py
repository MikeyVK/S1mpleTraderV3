"""Pure WorkphasesConfig schema for ConfigLoader-managed YAML loading."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PhaseDefinition(BaseModel):
    """Single phase definition from workphases.yaml."""

    display_name: str = ""
    description: str = ""
    commit_type_hint: str | None = None
    subphases: list[str] = Field(default_factory=list)
    exit_requires: list[dict[str, Any]] = Field(default_factory=list)
    entry_expects: list[dict[str, Any]] = Field(default_factory=list)


class WorkphasesConfig(BaseModel):
    """Read-only phase metadata value object."""

    version: str = ""
    phases: dict[str, PhaseDefinition] = Field(default_factory=dict)

    def get_exit_requires(self, phase: str) -> list[dict[str, Any]]:
        phase_definition = self.phases.get(phase)
        return list(phase_definition.exit_requires) if phase_definition is not None else []

    def get_entry_expects(self, phase: str) -> list[dict[str, Any]]:
        phase_definition = self.phases.get(phase)
        return list(phase_definition.entry_expects) if phase_definition is not None else []
