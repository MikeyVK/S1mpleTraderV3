# mcp_server/config/schemas/workphases.py
"""
Workphase metadata schema definitions.

Defines typed value objects for phase display metadata, entry expectations,
and exit requirements loaded by the configuration layer.

@layer: Backend (Config)
@dependencies: [pydantic, typing]
@responsibilities:
    - Define phase metadata and root workphase schema contracts
    - Validate workphase metadata structure
    - Provide entry and exit requirement lookup helpers
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class PhaseDefinition(BaseModel):
    """Single phase definition from workphases.yaml."""

    display_name: str = ""
    description: str = ""
    commit_type_hint: str | None = None
    subphases: list[str] = Field(default_factory=list)
    exit_requires: list[dict[str, Any]] = Field(default_factory=list)
    entry_expects: list[dict[str, Any]] = Field(default_factory=list)
    terminal: bool = False


class WorkphasesConfig(BaseModel):
    """Read-only phase metadata value object."""

    version: str = ""
    phases: dict[str, PhaseDefinition] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_single_terminal_phase(self) -> WorkphasesConfig:
        """Enforce exactly one terminal phase across all phases."""
        terminal = [name for name, phase in self.phases.items() if phase.terminal]
        if len(terminal) == 0:
            raise ValueError(
                "workphases.yaml must declare exactly one terminal phase. "
                "None found. Add 'terminal: true' to the intended phase."
            )
        if len(terminal) > 1:
            raise ValueError(
                f"workphases.yaml declares multiple terminal phases: {terminal}. "
                "Exactly one is permitted."
            )
        return self

    def get_terminal_phase(self) -> str:
        """Return the name of the single terminal phase. Guaranteed by validator."""
        return next(name for name, phase in self.phases.items() if phase.terminal)

    def get_exit_requires(self, phase: str) -> list[dict[str, Any]]:
        phase_definition = self.phases.get(phase)
        return list(phase_definition.exit_requires) if phase_definition is not None else []

    def get_entry_expects(self, phase: str) -> list[dict[str, Any]]:
        phase_definition = self.phases.get(phase)
        return list(phase_definition.entry_expects) if phase_definition is not None else []
