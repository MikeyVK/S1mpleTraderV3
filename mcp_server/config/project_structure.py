"""Project structure configuration model.

Purpose: Load and validate project_structure.yaml
Domain: WAAR (where artifacts can be created)
Cross-references: artifacts.yaml (validates allowed_artifact_types)
"""

from pathlib import Path
from typing import ClassVar, Dict, List, Optional, cast

import yaml
from pydantic import BaseModel, Field

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError


class DirectoryPolicy(BaseModel):
    """Directory-specific file and artifact policies."""

    path: str = Field(..., description="Directory path (workspace-relative)")
    parent: Optional[str] = Field(None, description="Parent directory path")
    description: str = Field(..., description="Human-readable description")
    allowed_artifact_types: List[str] = Field(
        default_factory=list,
        description="Artifact types allowed in this directory",
    )
    allowed_extensions: List[str] = Field(
        default_factory=list,
        description="File extensions allowed (empty = all allowed)",
    )
    require_scaffold_for: List[str] = Field(
        default_factory=list,
        description="Glob patterns requiring scaffolding",
    )

    @property
    def allowed_component_types(self) -> List[str]:
        """DEPRECATED: Backwards compatibility alias."""
        return self.allowed_artifact_types


class ProjectStructureConfig(BaseModel):
    """Project structure configuration (WAAR domain).

    Purpose: Define directory structure and file policies
    Loaded from: .st3/project_structure.yaml
    Used by: DirectoryPolicyResolver for path validation
    Cross-validates: allowed_artifact_types against artifacts.yaml
    """

    directories: Dict[str, DirectoryPolicy] = Field(
        ..., description="Directory policies keyed by directory path"
    )

    # Singleton pattern
    _instance: ClassVar[Optional["ProjectStructureConfig"]] = None

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
        instance._validate_artifact_types()
        instance._validate_parent_references()

        cls._instance = instance
        return cls._instance

    def _validate_artifact_types(self) -> None:
        """Cross-validate allowed_artifact_types against artifacts.yaml.

        Raises:
            ConfigError: If directory references unknown artifact type
        """
        artifact_config = ArtifactRegistryConfig.from_file()
        valid_types = set(artifact_config.list_type_ids())

        directories = cast(Dict[str, DirectoryPolicy], getattr(self, "directories"))
        for dir_path, policy in directories.items():
            invalid_types = set(policy.allowed_artifact_types) - valid_types
            if invalid_types:
                raise ConfigError(
                    f"Directory '{dir_path}' references unknown artifact types: "
                    f"{sorted(invalid_types)}. "
                    f"Valid types from artifacts.yaml: {sorted(valid_types)}",
                    file_path=".st3/project_structure.yaml",
                )

    def _validate_component_types(self) -> None:
        """DEPRECATED: Use _validate_artifact_types() instead."""
        return self._validate_artifact_types()

    def _validate_parent_references(self) -> None:
        """Validate parent directories exist in config.

        Raises:
            ConfigError: If directory references unknown parent
        """
        directories = cast(Dict[str, DirectoryPolicy], getattr(self, "directories"))
        for dir_path, policy in directories.items():
            parent = policy.parent
            if parent is not None and directories.get(parent) is None:
                raise ConfigError(
                    f"Directory '{dir_path}' references unknown parent: "
                    f"'{parent}'",
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
        directories = cast(Dict[str, DirectoryPolicy], getattr(self, "directories"))
        return directories.get(path)

    def get_all_directories(self) -> List[str]:
        """Get sorted list of all directory paths.

        Returns:
            Sorted list of directory paths
        """
        directories = cast(Dict[str, DirectoryPolicy], getattr(self, "directories"))
        return sorted(directories.keys())
