"""Pure project structure schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


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

    def get_directory(self, path: str) -> DirectoryPolicy | None:
        return self.directories.get(path)

    def get_all_directories(self) -> list[str]:
        return sorted(self.directories.keys())
