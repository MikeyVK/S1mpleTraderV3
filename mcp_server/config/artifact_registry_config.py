# mcp_server/config/artifact_registry_config.py
"""
Artifact Registry Configuration - Unified artifact type definitions.

Loads artifacts.yaml and provides artifact type definitions for the entire
scaffolding system. Replaces ComponentRegistryConfig with unified registry
supporting both code and document artifacts.

@layer: Backend (Config)
@dependencies: [pydantic, yaml, pathlib, typing]
@responsibilities:
    - Load and validate artifacts.yaml configuration
    - Provide artifact definitions via singleton pattern
    - Validate artifact type existence and field requirements
    - Support dependency injection and testing (reset_instance)
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp_server.core.exceptions import ConfigError


class ArtifactType(str, Enum):
    """Artifact category: code or document."""

    CODE = "code"
    DOC = "doc"


class StateMachineTransition(BaseModel):
    """State machine transition definition.
    
    Epic #18 will use this for validation.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_state: str = Field(..., alias="from", description="Source state")
    to_states: list[str] = Field(..., alias="to", description="Target states")


class StateMachine(BaseModel):
    """State machine definition for artifact lifecycle.
    
    Epic #18 will execute transitions.
    Issue #56 provides structure only.
    """

    states: list[str] = Field(..., description="All valid states")
    initial_state: str = Field(..., description="Starting state")
    valid_transitions: list[StateMachineTransition] = Field(
        default_factory=list, description="Allowed state transitions"
    )

    @field_validator("initial_state")
    @classmethod
    def validate_initial_state(cls, v: str, info) -> str:
        """Validate initial_state is in states list."""
        states = info.data.get("states", [])
        if v not in states:
            raise ValueError(
                f"Initial state '{v}' not in states list. "
                f"Available states: {', '.join(states)}. "
                f"Fix: Add '{v}' to states array or choose from "
                f"existing states."
            )
        return v


class ArtifactDefinition(BaseModel):
    """Single artifact type definition from artifacts.yaml."""

    type: ArtifactType = Field(..., description="code or doc")
    type_id: str = Field(
        ..., description="Unique identifier (e.g. 'dto', 'worker')"
    )
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Purpose description")

    # LEGACY fields (Issue #107 will remove after unified TemplateScaffolder)
    scaffolder_class: str | None = Field(
        None, description="LEGACY: Scaffolder class name"
    )
    scaffolder_module: str | None = Field(
        None, description="LEGACY: Scaffolder module path"
    )

    # Template configuration
    template_path: str | None = Field(None, description="Jinja2 template path")
    fallback_template: str | None = Field(
        None, description="Fallback template if primary missing"
    )
    name_suffix: str | None = Field(None, description="Default name suffix")
    file_extension: str = Field(..., description="File extension (.py, .md)")
    generate_test: bool = Field(False, description="Generate test file")

    # Scaffolding fields
    required_fields: list[str] = Field(
        default_factory=list, description="Required context fields"
    )
    optional_fields: list[str] = Field(
        default_factory=list, description="Optional context fields"
    )

    # State machine (Epic #18)
    state_machine: StateMachine = Field(
        ..., description="Lifecycle state machine"
    )

    @field_validator("type_id")
    @classmethod
    def validate_type_id(cls, v: str) -> str:
        """Validate type_id is lowercase with underscores."""
        if not v.islower() or not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                f"type_id '{v}' must be lowercase alphanumeric with "
                f"underscores. "
                f"Examples: 'dto', 'worker', 'research_doc'. "
                f"Fix: Convert to snake_case."
            )
        return v


class ArtifactRegistryConfig(BaseModel):
    """Artifact registry configuration loaded from artifacts.yaml.
    
    Singleton pattern: Use from_file() to get cached instance.
    
    Example:
        config = ArtifactRegistryConfig.from_file()
        dto_artifact = config.get_artifact("dto")
    """

    version: str = Field(..., description="Schema version")
    artifact_types: list[ArtifactDefinition] = Field(
        ..., description="All artifact definitions"
    )

    _instance: ClassVar[ArtifactRegistryConfig | None] = None
    _file_path: ClassVar[Path | None] = None

    @classmethod
    def from_file(
        cls, file_path: Path | None = None
    ) -> ArtifactRegistryConfig:
        """Load configuration from artifacts.yaml (singleton).
        
        Args:
            file_path: Path to artifacts.yaml (default: .st3/artifacts.yaml)
            
        Returns:
            Cached configuration instance
            
        Raises:
            ConfigError: File not found, invalid YAML, or validation failed
        """
        if file_path is None:
            file_path = Path(".st3/artifacts.yaml")

        # Return cached instance if same file
        if cls._instance is not None and cls._file_path == file_path:
            return cls._instance

        # Load and validate
        try:
            if not file_path.exists():
                raise ConfigError(
                    f"Artifact registry not found: {file_path}. "
                    f"Expected: .st3/artifacts.yaml. "
                    f"Fix: Run scaffold_design_doc with "
                    f"type='artifact_registry' or create manually."
                )

            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                raise ConfigError(
                    f"Empty artifact registry: {file_path}. "
                    f"Fix: Add artifact_types array with at least one "
                    f"artifact definition."
                )

            instance = cls.model_validate(data)
            cls._instance = instance
            cls._file_path = file_path
            return instance

        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {file_path}: {e}. "
                f"Fix: Check YAML syntax - common issues: incorrect "
                f"indentation, missing colons, "
                f"unquoted special characters. Use YAML validator."
            ) from e
        except Exception as e:
            if isinstance(e, ConfigError):
                raise
            raise ConfigError(
                f"Failed to load artifact registry: {e}. "
                f"Fix: Check file permissions and YAML structure."
            ) from e

    @classmethod
    def reset_instance(cls) -> None:
        """Clear singleton cache (for testing)."""
        cls._instance = None
        cls._file_path = None

    def get_artifact(self, type_id: str) -> ArtifactDefinition:
        """Get artifact definition by type_id.
        
        Args:
            type_id: Artifact type identifier (e.g. 'dto', 'worker')
            
        Returns:
            Artifact definition
            
        Raises:
            ConfigError: Artifact not found
        """
        for artifact in self.artifact_types:
            if artifact.type_id == type_id:
                return artifact

        available = ", ".join(a.type_id for a in self.artifact_types)
        raise ConfigError(
            f"Artifact type '{type_id}' not found in registry. "
            f"Available types: {available}. "
            f"Fix: Check spelling or add new type to "
            f".st3/artifacts.yaml."
        )

    def list_type_ids(
        self, artifact_type: ArtifactType | None = None
    ) -> list[str]:
        """List all artifact type_ids.
        
        Args:
            artifact_type: Filter by ArtifactType.CODE or .DOC (optional)
            
        Returns:
            List of type_ids
        """
        if artifact_type is None:
            return [a.type_id for a in self.artifact_types]
        return [
            a.type_id
            for a in self.artifact_types
            if a.type == artifact_type
        ]
