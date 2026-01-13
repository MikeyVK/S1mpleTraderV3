"""Component registry configuration model.

Purpose: Load and validate components.yaml
Domain: WAT (what can be scaffolded)
Cross-references: None (leaf config)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, ClassVar

import yaml
from pydantic import BaseModel, Field, field_validator

from mcp_server.core.errors import ConfigError


class ComponentDefinition(BaseModel):
    """Single component type definition."""

    type_id: str = Field(
        ..., description="Component type identifier (dto, worker, etc.)"
    )
    description: str = Field(
        ..., description="Human-readable description of component purpose"
    )
    scaffolder_class: str = Field(
        ...,
        description="Scaffolder class name for dynamic loading",
    )
    scaffolder_module: str = Field(
        ...,
        description="Module path for scaffolder class",
    )
    template_path: Optional[str] = Field(
        None, description="Path to Jinja2 template (relative to workspace root)"
    )
    fallback_template: Optional[str] = Field(
        None,
        description="Fallback template if primary template not found",
    )
    name_suffix: Optional[str] = Field(
        None,
        description="Auto-append suffix if missing (e.g., 'Worker' for workers)",
    )
    base_path: Optional[str] = Field(
        None, description="Default output directory for this component type"
    )
    test_base_path: Optional[str] = Field(
        None, description="Default test directory for this component type"
    )
    generate_test: bool = Field(
        True, description="Whether to generate test file by default"
    )
    required_fields: List[str] = Field(
        default_factory=list, description="Mandatory scaffold parameters"
    )
    optional_fields: List[str] = Field(
        default_factory=list, description="Optional scaffold parameters"
    )

    @field_validator("template_path")
    @classmethod
    def validate_template_exists(cls, v: Optional[str]) -> Optional[str]:
        """Validate template file exists (if specified)."""
        if v is None:
            return v  # Allow null for generic type

        template_file = Path(v)
        if not template_file.exists():
            raise ValueError(
                f"Template file not found: {v}. "
                f"Expected template at workspace root."
            )
        return v

    @field_validator("fallback_template")
    @classmethod
    def validate_fallback_exists(cls, v: Optional[str]) -> Optional[str]:
        """Validate fallback template exists (if specified)."""
        if v is None:
            return v

        fallback_file = Path(v)
        if not fallback_file.exists():
            raise ValueError(
                f"Fallback template not found: {v}. "
                f"Expected template at workspace root."
            )
        return v

    def has_required_field(self, field_name: str) -> bool:
        """Check if field is required for this component type."""
        return field_name in self.required_fields

    def has_optional_field(self, field_name: str) -> bool:
        """Check if field is optional for this component type."""
        return field_name in self.optional_fields

    def all_fields(self) -> List[str]:
        """Get all fields (required + optional)."""
        return self.required_fields + self.optional_fields

    def validate_scaffold_fields(self, provided: Dict[str, Any]) -> None:
        """Validate provided fields meet requirements.

        Args:
            provided: Dict of field names to values provided for scaffolding

        Raises:
            ValueError: If required fields are missing
        """
        missing = set(self.required_fields) - set(provided.keys())
        if missing:
            raise ValueError(
                f"Missing required fields for {self.type_id}: {sorted(missing)}"
            )


class ComponentRegistryConfig(BaseModel):
    """Component registry configuration (WAT domain).

    Purpose: Single source of truth for component type definitions
    Loaded from: .st3/components.yaml
    Used by: ScaffoldComponentTool, DirectoryPolicyResolver (indirect)
    """

    components: Dict[str, ComponentDefinition] = Field(
        ..., description="Component type definitions keyed by type_id"
    )

    # Singleton pattern - use ClassVar to prevent Pydantic field interpretation
    singleton_instance: ClassVar[Optional["ComponentRegistryConfig"]] = None

    @classmethod
    def from_file(
        cls, config_path: str = ".st3/components.yaml"
    ) -> "ComponentRegistryConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            config_path: Path to components.yaml file

        Returns:
            Singleton instance of ComponentRegistryConfig

        Raises:
            ConfigError: If file not found or YAML invalid
        """
        # Return cached instance if exists
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        # Load and parse YAML
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}", file_path=config_path
            )

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path}: {e}", file_path=config_path
            ) from e

        # Validate structure
        if "component_types" not in data:
            raise ConfigError(
                f"Missing 'component_types' key in {config_path}",
                file_path=config_path,
            )

        # Transform to ComponentDefinition instances
        components = {}
        for type_id, comp_data in data["component_types"].items():
            try:
                # Add type_id to data
                comp_data_with_id = {"type_id": type_id, **comp_data}
                components[type_id] = ComponentDefinition(**comp_data_with_id)
            except Exception as e:
                raise ConfigError(
                    f"Invalid component definition for '{type_id}': {e}",
                    file_path=config_path,
                ) from e

        # Create and cache instance
        cls.singleton_instance = cls(components=components)
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls.singleton_instance = None

    def get_component(self, type_id: str) -> ComponentDefinition:
        """Get component definition by type ID.

        Args:
            type_id: Component type identifier (dto, worker, etc.)

        Returns:
            ComponentDefinition for requested type

        Raises:
            ValueError: If type_id not found in registry
        """
        if type_id not in self.components:
            available = sorted(self.components.keys())
            raise ValueError(
                f"Unknown component type: '{type_id}'. Available: {available}"
            )
        return self.components[type_id]

    def get_available_types(self) -> List[str]:
        """Get list of all registered component type IDs.

        Returns:
            Sorted list of component type identifiers
        """
        return sorted(self.components.keys())

    def has_component_type(self, type_id: str) -> bool:
        """Check if component type exists in registry.

        Args:
            type_id: Component type identifier to check

        Returns:
            True if type exists, False otherwise
        """
        return type_id in self.components
