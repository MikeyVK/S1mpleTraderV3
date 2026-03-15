"""Pure operation policies schema definitions."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from mcp_server.config.schemas.workflows import WorkflowConfig
from mcp_server.core.exceptions import ConfigError


class OperationPolicy(BaseModel):
    """Single operation policy definition."""

    operation_id: str = Field(..., description="Operation identifier")
    description: str = Field(..., description="Human-readable description of operation")
    allowed_phases: list[str] = Field(default_factory=list)
    blocked_patterns: list[str] = Field(default_factory=list)
    allowed_extensions: list[str] = Field(default_factory=list)
    require_tdd_prefix: bool = Field(False)
    allowed_prefixes: list[str] = Field(default_factory=list)

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extension_format(cls, value: list[str]) -> list[str]:
        for extension in value:
            if not extension.startswith("."):
                raise ValueError(
                    f"File extension must start with dot: '{extension}' should be '.{extension}'"
                )
        return value

    def is_allowed_in_phase(self, phase: str) -> bool:
        return not self.allowed_phases or phase in self.allowed_phases

    def is_path_blocked(self, path: str) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.blocked_patterns)

    def is_extension_allowed(self, path: str) -> bool:
        if not self.allowed_extensions:
            return True
        return Path(path).suffix in self.allowed_extensions

    def validate_commit_message(self, message: str) -> bool:
        if not self.require_tdd_prefix:
            return True
        return any(message.startswith(prefix) for prefix in self.allowed_prefixes)


class OperationPoliciesConfig(BaseModel):
    """Operation policies configuration value object."""

    operations: dict[str, OperationPolicy] = Field(...)
    workflow_config: WorkflowConfig | None = Field(default=None, exclude=True)

    def validate_phases(self) -> None:
        valid_phases: set[str] = set()
        if self.workflow_config is None:
            raise ConfigError(
                "Workflow config is required for phase cross-validation",
                file_path=".st3/workflows.yaml",
            )

        for workflow in self.workflow_config.workflows.values():
            valid_phases.update(workflow.phases)

        for operation_id, policy in self.operations.items():
            invalid_phases = set(policy.allowed_phases) - valid_phases
            if invalid_phases:
                raise ConfigError(
                    f"Operation '{operation_id}' references unknown phases: "
                    f"{sorted(invalid_phases)}. Valid phases from workflows.yaml: "
                    f"{sorted(valid_phases)}",
                    file_path=".st3/policies.yaml",
                )

    def get_operation_policy(self, operation_id: str) -> OperationPolicy:
        if operation_id not in self.operations:
            raise ValueError(
                f"Unknown operation: '{operation_id}'. "
                f"Available operations: {sorted(self.operations.keys())}"
            )
        return self.operations[operation_id]

    def get_available_operations(self) -> list[str]:
        return sorted(self.operations.keys())
