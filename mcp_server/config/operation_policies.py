"""Legacy compatibility wrapper for OperationPoliciesConfig during C_LOADER migration."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.operation_policies_config import (
    OperationPoliciesConfig as _OperationPoliciesConfigSchema,
)
from mcp_server.config.schemas.operation_policies_config import OperationPolicy
from mcp_server.config.workflows import WorkflowConfig

__all__ = ["OperationPoliciesConfig", "OperationPolicy"]


class OperationPoliciesConfig(_OperationPoliciesConfigSchema):
    """Compatibility surface for pre-C_LOADER consumers."""

    singleton_instance: ClassVar[OperationPoliciesConfig | None] = None

    @classmethod
    def from_file(
        cls,
        config_path: str = ".st3/config/policies.yaml",
        workflow_config: WorkflowConfig | None = None,
    ) -> OperationPoliciesConfig:
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        path = Path(config_path)
        loader = ConfigLoader(config_root=path.parent)
        loaded = loader.load_operation_policies_config(
            config_path=path,
            workflow_config=workflow_config,
        )
        instance = cls.model_validate(loaded.model_dump())
        instance.workflow_config = loaded.workflow_config  # type: ignore[attr-defined]
        cls.singleton_instance = instance
        return instance

    @classmethod
    def reset_instance(cls) -> None:
        cls.singleton_instance = None
