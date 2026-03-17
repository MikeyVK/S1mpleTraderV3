"""Legacy compatibility wrapper for ArtifactRegistryConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import yaml

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.artifact_registry_config import (
    ArtifactDefinition,
    ArtifactType,
    StateMachine,
    StateMachineTransition,
)
from mcp_server.config.schemas.artifact_registry_config import (
    ArtifactRegistryConfig as _ArtifactRegistryConfigSchema,
)
from mcp_server.core.exceptions import ConfigError

__all__ = [
    "ArtifactDefinition",
    "ArtifactRegistryConfig",
    "ArtifactType",
    "StateMachine",
    "StateMachineTransition",
]


class ArtifactRegistryConfig(_ArtifactRegistryConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    _instance: ClassVar[ArtifactRegistryConfig | None] = None
    _file_path: ClassVar[Path | None] = None

    def get_artifact(self, type_id: str) -> ArtifactDefinition:
        try:
            return super().get_artifact(type_id)
        except ConfigError as exc:
            file_path = str(self._file_path or Path(".st3/config/artifacts.yaml"))
            raise ConfigError(exc.message, file_path=file_path, hints=exc.hints) from exc

    @classmethod
    def from_file(cls, file_path: Path | None = None) -> ArtifactRegistryConfig:
        config_path = Path(".st3/config/artifacts.yaml") if file_path is None else Path(file_path)
        if cls._instance is not None and cls._file_path == config_path:
            return cls._instance

        loader = ConfigLoader(config_root=config_path.parent)
        try:
            loaded = loader.load_artifact_registry_config(config_path=config_path)
        except ConfigError:
            raise
        except yaml.YAMLError as exc:
            raise ConfigError(
                "Invalid YAML syntax: "
                f"{exc}. Fix: Check YAML syntax - common issues: incorrect "
                "indentation, missing colons, unquoted special characters. "
                "Use YAML validator.",
                file_path=str(config_path),
            ) from exc

        instance = cls.model_validate(loaded.model_dump())
        cls._instance = instance
        cls._file_path = config_path
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None
        cls._file_path = None
