"""Legacy compatibility wrapper for ScaffoldMetadataConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.scaffold_metadata_config import (
    CommentPattern,
    MetadataField,
)
from mcp_server.config.schemas.scaffold_metadata_config import (
    ScaffoldMetadataConfig as _ScaffoldMetadataConfigSchema,
)
from mcp_server.core.exceptions import ConfigError

__all__ = ["CommentPattern", "ConfigError", "MetadataField", "ScaffoldMetadataConfig"]


class ScaffoldMetadataConfig(_ScaffoldMetadataConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    @classmethod
    def from_file(cls, path: Path | None = None) -> ScaffoldMetadataConfig:
        config_path = Path(".st3/scaffold_metadata.yaml") if path is None else Path(path)
        loader = ConfigLoader(config_root=config_path.parent)
        loaded = loader.load_scaffold_metadata_config(config_path=config_path)
        return cls.model_validate(loaded.model_dump())
