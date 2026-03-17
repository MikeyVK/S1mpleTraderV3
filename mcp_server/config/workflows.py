"""Legacy compatibility wrapper for WorkflowConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import ValidationError

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.workflows import WorkflowConfig as _WorkflowConfigSchema
from mcp_server.config.schemas.workflows import WorkflowTemplate
from mcp_server.core.exceptions import ConfigError

__all__ = ["WorkflowConfig", "WorkflowTemplate"]


class WorkflowConfig(_WorkflowConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[WorkflowConfig | None] = None

    @classmethod
    def load(cls, path: Path | None = None) -> WorkflowConfig:
        config_path = Path(".st3/config/workflows.yaml") if path is None else Path(path)
        if path is None and cls.singleton_instance is not None:
            return cls.singleton_instance

        if not config_path.exists():
            raise FileNotFoundError(
                f"Workflow config not found: {config_path}\n"
                f"Expected location: .st3/config/workflows.yaml\n"
                f"Hint: Initialize workflows with default config"
            )

        loader = ConfigLoader(config_root=config_path.parent)
        try:
            loaded = loader.load_workflow_config(config_path=config_path)
        except ConfigError as exc:
            cause = exc.__cause__
            if isinstance(cause, (yaml.YAMLError, ValidationError)):
                raise cause from exc
            raise

        instance = cls.model_validate(loaded.model_dump())
        if path is None:
            cls.singleton_instance = instance
        return instance

    @classmethod
    def from_file(cls, path: str = ".st3/config/workflows.yaml") -> WorkflowConfig:
        if cls.singleton_instance is None or path != ".st3/config/workflows.yaml":
            return cls.load(Path(path))
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
