"""Pure project structure schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mcp_server.config.schemas.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError


class DirectoryPolicy(BaseModel):
    """Directory-specific file and artifact policies."""

    path: str = Field(..., description="Directory path (workspace-relative)")
    parent: str | None = Field(None, description="Parent directory path")
    description: str = Field(..., description="Human-readable description")
    allowed_artifact_types: list[str] = Field(default_factory=list)
    allowed_extensions: list[str] = Field(default_factory=list)
    require_scaffold_for: list[str] = Field(default_factory=list)

    @property
    def allowed_component_types(self) -> list[str]:
        return self.allowed_artifact_types


class ProjectStructureConfig(BaseModel):
    """Project structure configuration value object."""

    directories: dict[str, DirectoryPolicy] = Field(...)
    artifact_registry: ArtifactRegistryConfig | None = Field(default=None, exclude=True)

    def validate_artifact_types(self) -> None:
        if self.artifact_registry is None:
            raise ConfigError(
                "Artifact registry is required for project structure cross-validation",
                file_path=".st3/artifacts.yaml",
            )
        valid_types = set(self.artifact_registry.list_type_ids())
        for directory_path, policy in self.directories.items():
            invalid_types = set(policy.allowed_artifact_types) - valid_types
            if invalid_types:
                raise ConfigError(
                    f"Directory '{directory_path}' references unknown artifact types: "
                    f"{sorted(invalid_types)}. Valid types from artifacts.yaml: "
                    f"{sorted(valid_types)}",
                    file_path=".st3/project_structure.yaml",
                )

    def _validate_component_types(self) -> None:
        self.validate_artifact_types()

    def validate_parent_references(self) -> None:
        for directory_path, policy in self.directories.items():
            if policy.parent is not None and policy.parent not in self.directories:
                raise ConfigError(
                    f"Directory '{directory_path}' references unknown parent: '{policy.parent}'",
                    file_path=".st3/project_structure.yaml",
                )

    def get_directory(self, path: str) -> DirectoryPolicy | None:
        return self.directories.get(path)

    def get_all_directories(self) -> list[str]:
        return sorted(self.directories.keys())
