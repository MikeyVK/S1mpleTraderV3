"""Legacy compatibility wrapper for MilestoneConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.milestone_config import MilestoneConfig as _MilestoneConfigSchema
from mcp_server.config.schemas.milestone_config import MilestoneEntry

__all__ = ["MilestoneConfig", "MilestoneEntry"]


class MilestoneConfig(_MilestoneConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[MilestoneConfig | None] = None

    @classmethod
    def from_file(cls, path: str = ".st3/milestones.yaml") -> MilestoneConfig:
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Milestone config not found: {path}. "
                "Create .st3/milestones.yaml (empty list is valid)."
            )

        loader = ConfigLoader(config_root=config_path.parent)
        loaded = loader.load_milestone_config(config_path=config_path)

        instance = cls.model_validate(loaded.model_dump())
        cls.singleton_instance = instance
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
