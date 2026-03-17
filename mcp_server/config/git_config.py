"""Legacy compatibility wrapper for GitConfig during C_LOADER migration."""

from pathlib import Path
from typing import ClassVar, Optional

from mcp_server.config.compat_roots import normalize_config_file_path
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.git_config import GitConfig as _GitConfigSchema
from mcp_server.core.exceptions import ConfigError


class GitConfig(_GitConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[Optional["GitConfig"]] = None
    _loaded_path: ClassVar[Path | None] = None

    @classmethod
    def from_file(cls, path: str = ".st3/config/git.yaml") -> "GitConfig":
        config_path = Path(path)
        normalized_path = normalize_config_file_path(config_path)

        if cls.singleton_instance is not None and cls._loaded_path == normalized_path:
            return cls.singleton_instance

        loader = ConfigLoader(config_root=normalized_path.parent)
        try:
            loaded = loader.load_git_config(config_path=normalized_path)
        except ConfigError as exc:
            if exc.file_path == str(normalized_path) and "not found" in exc.message.lower():
                raise FileNotFoundError(f"Git config not found: {config_path}") from exc
            raise

        instance = cls.model_validate(loaded.model_dump())

        cls.singleton_instance = instance
        cls._loaded_path = normalized_path
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
        cls._loaded_path = None
        cls._compiled_pattern = None
