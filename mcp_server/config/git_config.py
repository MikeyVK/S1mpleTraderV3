"""Legacy compatibility wrapper for GitConfig during C_LOADER migration."""

from pathlib import Path
from typing import ClassVar, Optional

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.git_config import GitConfig as _GitConfigSchema
from mcp_server.core.exceptions import ConfigError


class GitConfig(_GitConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[Optional["GitConfig"]] = None

    @classmethod
    def from_file(cls, path: str = ".st3/git.yaml") -> "GitConfig":
        config_path = Path(path)
        if path == ".st3/git.yaml" and cls.singleton_instance is not None:
            return cls.singleton_instance

        loader = ConfigLoader(config_root=config_path.parent)
        try:
            loaded = loader.load_git_config(config_path=config_path)
        except ConfigError as exc:
            if exc.file_path == str(config_path) and "not found" in exc.message.lower():
                raise FileNotFoundError(f"Git config not found: {config_path}") from exc
            raise

        instance = cls.model_validate(loaded.model_dump())

        cls.singleton_instance = instance
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
        cls._compiled_pattern = None
