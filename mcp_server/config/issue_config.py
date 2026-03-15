"""Legacy compatibility wrapper for IssueConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.issue_config import IssueConfig as _IssueConfigSchema
from mcp_server.config.schemas.issue_config import IssueTypeEntry

__all__ = ["IssueConfig", "IssueTypeEntry"]


class IssueConfig(_IssueConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[IssueConfig | None] = None

    @classmethod
    def from_file(cls, path: str = ".st3/issues.yaml") -> IssueConfig:
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Issue config not found: {path}. "
                "Create .st3/issues.yaml with issue type conventions."
            )

        loader = ConfigLoader(config_root=config_path.parent)
        loaded = loader.load_issue_config(config_path=config_path)

        instance = cls.model_validate(loaded.model_dump())
        cls.singleton_instance = instance
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
