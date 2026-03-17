"""Legacy compatibility wrapper for ScopeConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.scope_config import ScopeConfig as _ScopeConfigSchema


class ScopeConfig(_ScopeConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[ScopeConfig | None] = None
    _loaded_path: ClassVar[Path | None] = None

    @classmethod
    def from_file(cls, path: str = ".st3/config/scopes.yaml") -> ScopeConfig:
        config_path = Path(path)
        if cls.singleton_instance is not None and cls._loaded_path == config_path:
            return cls.singleton_instance

        if not config_path.exists():
            raise FileNotFoundError(
                f"Scope config not found: {path}. Create .st3/config/scopes.yaml with valid scope names."
            )

        loader = ConfigLoader(config_root=config_path.parent)
        loaded = loader.load_scope_config(config_path=config_path)
        instance = cls.model_validate(loaded.model_dump())
        cls.singleton_instance = instance
        cls._loaded_path = config_path
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
        cls._loaded_path = None
