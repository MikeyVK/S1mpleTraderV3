"""Legacy compatibility wrapper for ProjectStructureConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.project_structure_config import (
    DirectoryPolicy,
)
from mcp_server.config.schemas.project_structure_config import (
    ProjectStructureConfig as _ProjectStructureConfigSchema,
)

__all__ = ["DirectoryPolicy", "ProjectStructureConfig"]


class ProjectStructureConfig(_ProjectStructureConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    _instance: ClassVar[ProjectStructureConfig | None] = None

    @classmethod
    def from_file(
        cls, config_path: str = ".st3/config/project_structure.yaml"
    ) -> ProjectStructureConfig:
        if cls._instance is not None:
            return cls._instance

        path = Path(config_path)
        loader = ConfigLoader(config_root=path.parent)
        artifact_registry = loader.load_artifact_registry_config()
        loaded = loader.load_project_structure_config(
            config_path=path,
            artifact_registry=artifact_registry,
        )
        instance = cls.model_validate(loaded.model_dump())
        instance.artifact_registry = loaded.artifact_registry  # type: ignore[attr-defined]
        cls._instance = instance
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None
