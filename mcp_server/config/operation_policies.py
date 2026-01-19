# mcp_server/config/operation_policies.py
"""Operation policy configuration from policies.yaml.

Defines which operations (e.g., 'commit', 'push', 'merge') are allowed
in which workflow phases (e.g., 'red', 'green', 'refactor').

Supports:
- Per-operation allowed_phases
- Cross-validation against workflows.yaml
- Human approval requirements
- Policy inheritance (future)

@layer: Backend (Configuration)
@dependencies: [workflows.yaml, policies.yaml]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field
from mcp_server.config.workflows import WorkflowConfig, WorkflowTemplate
from mcp_server.core.exceptions import ConfigError

# Load workflows config once for cross-validation
workflow_config = WorkflowConfig.load()


class OperationPolicy(BaseModel):
    """Single operation policy definition."""

    allowed_phases: list[str] = Field(
        ..., description="Phases where operation is allowed"
    )
    requires_human_approval: bool = Field(
        default=False, description="Human approval required"
    )
    description: str | None = Field(None, description="Policy description")


class OperationPolicyConfig(BaseModel):
    """Operation policy configuration from policies.yaml.

    Singleton pattern: use from_file() to get cached instance.

    Example:
        config = OperationPolicyConfig.from_file()
        commit_policy = config.get_operation_policy('commit')
    """

    version: str = Field(..., description="Schema version")
    operations: dict[str, OperationPolicy] = Field(
        ..., description="Operation policies"
    )

    singleton_instance: ClassVar[OperationPolicyConfig | None] = None

    def __init__(self, **data: Any) -> None:
        """Initialize and cross-validate against workflows.yaml."""
        super().__init__(**data)
        self._validate_phases()

    @classmethod
    def from_file(
        cls,
        file_path: Path | None = None,
    ) -> OperationPolicyConfig:
        """Load configuration from policies.yaml (singleton).

        Args:
            file_path: Path to policies.yaml (default: .st3/policies.yaml)

        Returns:
            Cached configuration instance

        Raises:
            ConfigError: File not found, invalid YAML, or validation failed
        """
        if file_path is None:
            file_path = Path(".st3/policies.yaml")
        else:
            file_path = Path(file_path)

        # Return cached instance if exists
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        # Load and validate
        try:
            if not file_path.exists():
                raise ConfigError(
                    f"Policy config not found: {file_path}. "
                    f"Expected: .st3/policies.yaml. "
                    f"Fix: Restore config from backup.",
                    file_path=str(file_path),
                )

            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                raise ConfigError(
                    f"Empty policy config: {file_path}. "
                    f"Expected: 'version' and 'operations' keys. "
                    f"Fix: Restore config from backup.",
                    file_path=str(file_path),
                )

        except FileNotFoundError as e:
            raise ConfigError(
                f"Policy config not found: {file_path}",
                file_path=str(file_path),
            ) from e
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in policy config: {e}",
                file_path=str(file_path),
            ) from e
        except Exception as e:
            raise ConfigError(
                f"Failed to load policy config: {e}",
                file_path=str(file_path),
            ) from e

        # Create instance
        try:
            instance = cls(**data)
        except Exception as e:
            raise ConfigError(
                f"Invalid policy config schema: {e}. "
                f"Fix: Check policies.yaml structure matches schema.",
                file_path=str(file_path),
            ) from e

        # Cache and return
        cls.singleton_instance = instance
        return cls.singleton_instance

    def _validate_phases(self) -> None:
        """Cross-validate allowed_phases against workflows.yaml.

        Raises:
            ConfigError: If any operation references unknown phase
        """
        # Cast to concrete dicts for explicit typing
        workflows_dict: dict[str, WorkflowTemplate] = dict(workflow_config.workflows)
        valid_phases: set[str] = set()
        try:
            for wf_template in workflows_dict.values():
                valid_phases.update(wf_template.phases)
        except Exception as e:
            raise ConfigError(
                f"Failed to load workflows.yaml for cross-validation: {e}",
                file_path=".st3/workflows.yaml",
            ) from e

        operations_dict: dict[str, OperationPolicy] = dict(self.operations)
        for op_id, policy in operations_dict.items():
            invalid_phases = set(policy.allowed_phases) - valid_phases
            if invalid_phases:
                raise ConfigError(
                    f"Operation '{op_id}' references unknown phases: "
                    f"{sorted(invalid_phases)}. "
                    f"Valid phases from workflows.yaml: {sorted(valid_phases)}",
                    file_path=".st3/policies.yaml",
                )

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls.singleton_instance = None

    def get_operation_policy(self, operation_id: str) -> OperationPolicy:
        """Get policy for specific operation.

        Args:
            operation_id: Operation identifier (scaffold, create_file, commit)

        Returns:
            OperationPolicy for requested operation

        Raises:
            ValueError: If operation_id not found in config
        """
        operations_dict: dict[str, OperationPolicy] = dict(self.operations)
        if operation_id not in operations_dict:
            raise ValueError(
                f"Unknown operation: '{operation_id}'. "
                f"Available operations: {sorted(operations_dict.keys())}"
            )
        return operations_dict[operation_id]

    def get_available_operations(self) -> list[str]:
        """Get list of all configured operation IDs.

        Returns:
            Sorted list of operation identifiers
        """
        operations_dict: dict[str, OperationPolicy] = dict(self.operations)
        return sorted(operations_dict.keys())
