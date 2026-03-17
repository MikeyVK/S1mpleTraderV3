"""Pure artifact registry schema definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from mcp_server.core.exceptions import ConfigError


class ArtifactType(str, Enum):
    """Artifact category: code, documentation, or tracking."""

    CODE = "code"
    DOC = "doc"
    TRACKING = "tracking"


class StateMachineTransition(BaseModel):
    """State machine transition definition."""

    model_config = ConfigDict(populate_by_name=True)

    from_state: str = Field(..., alias="from", description="Source state")
    to_states: list[str] = Field(..., alias="to", description="Target states")


class StateMachine(BaseModel):
    """State machine definition for artifact lifecycle."""

    states: list[str] = Field(..., description="All valid states")
    initial_state: str = Field(..., description="Starting state")
    valid_transitions: list[StateMachineTransition] = Field(
        default_factory=list,
        description="Allowed state transitions",
    )

    @field_validator("initial_state")
    @classmethod
    def validate_initial_state(cls, value: str, info: ValidationInfo) -> str:
        states = info.data.get("states", [])
        if value not in states:
            raise ValueError(
                f"Initial state '{value}' not in states list. "
                f"Available states: {', '.join(states)}. "
                f"Fix: Add '{value}' to states array or choose from existing states."
            )
        return value


class ArtifactDefinition(BaseModel):
    """Single artifact type definition from artifacts.yaml."""

    type: ArtifactType = Field(..., description="code or doc")
    type_id: str = Field(..., description="Unique identifier (e.g. 'dto', 'worker')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Purpose description")
    output_type: Literal["file", "ephemeral"] = Field(
        "file",
        description="Output type: 'file' for disk artifacts, 'ephemeral' for in-memory.",
    )
    scaffolder_class: str | None = Field(None, description="LEGACY: Scaffolder class name")
    scaffolder_module: str | None = Field(None, description="LEGACY: Scaffolder module path")
    template_path: str | None = Field(None, description="Jinja2 template path")
    fallback_template: str | None = Field(None, description="Fallback template if primary missing")
    name_suffix: str | None = Field(None, description="Default name suffix")
    file_extension: str = Field(..., description="File extension (.py, .md)")
    generate_test: bool = Field(False, description="Generate test file")
    required_fields: list[str] = Field(default_factory=list, description="Required context fields")
    optional_fields: list[str] = Field(default_factory=list, description="Optional context fields")
    state_machine: StateMachine = Field(..., description="Lifecycle state machine")

    def validate_artifact_fields(self, provided: dict[str, Any]) -> None:
        missing = set(self.required_fields) - set(provided.keys())
        if missing:
            raise ValueError(f"Missing required fields for {self.type_id}: {sorted(missing)}")

    @field_validator("type_id")
    @classmethod
    def validate_type_id(cls, value: str) -> str:
        if not value.islower() or not all(ch.isalnum() or ch == "_" for ch in value):
            raise ValueError(
                f"type_id '{value}' must be lowercase alphanumeric with underscores. "
                f"Examples: 'dto', 'worker', 'research_doc'. Fix: Convert to snake_case."
            )
        return value


class ArtifactRegistryConfig(BaseModel):
    """Artifact registry configuration value object."""

    version: str = Field(..., description="Schema version")
    artifact_types: list[ArtifactDefinition] = Field(..., description="All artifact definitions")

    def get_artifact(self, type_id: str) -> ArtifactDefinition:
        for artifact in self.artifact_types:
            if artifact.type_id == type_id:
                return artifact

        available = ", ".join(artifact.type_id for artifact in self.artifact_types)
        raise ConfigError(
            f"Artifact type '{type_id}' not found in registry. "
            f"Available types: {available}. Fix: Check spelling or add new type "
            "to .st3/config/artifacts.yaml.",
            hints=[
                f"Check spelling: '{type_id}' not found",
                f"Available types: {available}",
                "Add new type to .st3/config/artifacts.yaml if needed",
            ],
        )

    def list_type_ids(self, artifact_type: ArtifactType | None = None) -> list[str]:
        if artifact_type is None:
            return sorted(artifact.type_id for artifact in self.artifact_types)
        return sorted(
            artifact.type_id for artifact in self.artifact_types if artifact.type == artifact_type
        )

    def has_artifact_type(self, type_id: str) -> bool:
        return any(artifact.type_id == type_id for artifact in self.artifact_types)
