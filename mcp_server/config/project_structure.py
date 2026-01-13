"""Project structure configuration model.

Purpose: Load and validate project_structure.yaml
Domain: WAAR (where components can be created)
Cross-references: components.yaml (validates allowed_component_types)
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from mcp_server.config.component_registry import ComponentRegistryConfig
from mcp_server.core.errors import ConfigError


class DirectoryPolicy(BaseModel):
    """Directory-specific file and component policies."""

    path: str = Field(..., description="Directory path (workspace-relative)")
    parent: Optional[str] = Field(None, description="Parent directory path")
    description: str = Field(..., description="Human-readable description")
    allowed_component_types: List[str] = Field(
        default_factory=list,
        description="Component types allowed in this directory",
    )
    allowed_extensions: List[str] = Field(
        default_factory=list,
        description="File extensions allowed (empty = all allowed)",
    )
    require_scaffold_for: List[str] = Field(
        default_factory=list,
        description="Glob patterns requiring scaffolding",
    )


class ProjectStructureConfig(BaseModel):
    """Project structure configuration (WAAR domain).

    Purpose: Define directory structure and file policies
    Loaded from: .st3/project_structure.yaml
    Used by: DirectoryPolicyResolver for path validation
    Cross-validates: allowed_component_types against components.yaml
    """

    directories: Dict[str, DirectoryPolicy] = Field(
        ..., description="Directory policies keyed by directory path"
    )

    # Singleton pattern
    _instance: Optional["ProjectStructureConfig"] = None

    @classmethod
    def from_file(
        cls, config_path: str = ".st3/project_structure.yaml"
    ) -> "ProjectStructureConfig":
        """Load config from YAML file with cross-validation.

        Args:
            config_path: Path to project_structure.yaml file

        Returns:
            Singleton instance of ProjectStructureConfig

        Raises:
            ConfigError: If file not found, YAML invalid, or validation fails
        """
        if cls._instance is not None:
            return cls._instance

        # Load YAML
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
        if "directories" not in data:
            raise ConfigError(
                f"Missing 'directories' key in {config_path}",
                file_path=config_path,
            )

        # Transform to DirectoryPolicy instances
        directories = {}
        for dir_path, dir_data in data["directories"].items():
            try:
                directories[dir_path] = DirectoryPolicy(path=dir_path, **dir_data)
            except Exception as e:
                raise ConfigError(
                    f"Invalid directory policy for '{dir_path}': {e}",
                    file_path=config_path,
                ) from e

        instance = cls(directories=directories)

        # Cross-validation
        instance._validate_component_types()
        instance._validate_parent_references()

        cls._instance = instance
        return cls._instance

    def _validate_component_types(self) -> None:
        """Cross-validate allowed_component_types against components.yaml.

        Raises:
            ConfigError: If directory references unknown component type
        """
        component_config = ComponentRegistryConfig.from_file()
        valid_types = set(component_config.get_available_types())

        for dir_path, policy in self.directories.items():
            invalid_types = set(policy.allowed_component_types) - valid_types
            if invalid_types:
                raise ConfigError(
                    f"Directory '{dir_path}' references unknown component types: "
                    f"{sorted(invalid_types)}. "
                    f"Valid types from components.yaml: {sorted(valid_types)}",
                    file_path=".st3/project_structure.yaml",
                )

    def _validate_parent_references(self) -> None:
        """Validate parent directories exist in config.

        Raises:
            ConfigError: If directory references unknown parent
        """
        for dir_path, policy in self.directories.items():
            if policy.parent is not None and policy.parent not in self.directories:
                raise ConfigError(
                    f"Directory '{dir_path}' references unknown parent: "
                    f"'{policy.parent}'",
                    file_path=".st3/project_structure.yaml",
                )

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls._instance = None

    def get_directory(self, path: str) -> Optional[DirectoryPolicy]:
        """Get policy for exact directory path.

        Args:
            path: Directory path to look up

        Returns:
            DirectoryPolicy if found, None otherwise
        """
        return self.directories.get(path)

    def get_all_directories(self) -> List[str]:
        """Get sorted list of all directory paths.

        Returns:
            Sorted list of directory paths
        """
        return sorted(self.directories.keys())
