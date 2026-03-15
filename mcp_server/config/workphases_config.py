"""Legacy compatibility wrapper for WorkphasesConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.workphases import (
    PhaseDefinition,
)
from mcp_server.config.schemas.workphases import (
    WorkphasesConfig as _WorkphasesConfigSchema,
)

__all__ = ["PhaseDefinition", "WorkphasesConfig"]


class WorkphasesConfig(_WorkphasesConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    def __init__(self, path: Path) -> None:
        config_path = Path(path)
        loader = ConfigLoader(config_root=config_path.parent)
        loaded = loader.load_workphases_config(config_path=config_path)
        super().__init__(**loaded.model_dump())
