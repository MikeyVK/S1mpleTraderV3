"""Operation policies configuration model.

Purpose: Load and validate policies.yaml
Domain: WANNEER (when operations are allowed)
Cross-references: workflows.yaml (validates allowed_phases exist)
"""
# pyright: reportAttributeAccessIssue=false  # Pydantic Field → runtime dict

import fnmatch
from pathlib import Path
from typing import ClassVar, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from mcp_server.config.workflows import workflow_config
from mcp_server.core.exceptions import ConfigError


class OperationPolicy(BaseModel):
    """Single operation policy definition."""

    operation_id: str = Field(
        ..., description="Operation identifier (scaffold, create_file, commit)"
    )
    description: str = Field(
        ..., description="Human-readable description of operation"
    )
    allowed_phases: List[str] = Field(
        default_factory=list,
        description="Phases where operation allowed (empty = all phases)",
    )
    blocked_patterns: List[str] = Field(
        default_factory=list, description="Glob patterns for blocked file paths"
    )
    allowed_extensions: List[str] = Field(
        default_factory=list,
        description="File extensions allowed (empty = all extensions)",
    )
    require_tdd_prefix: bool = Field(
        False, description="Require TDD prefix in commit messages"
    )
    allowed_prefixes: List[str] = Field(
        default_factory=list, description="Valid TDD prefixes for commit messages"
    )

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extension_format(cls, v: List[str]) -> List[str]:
        """Validate extensions have leading dot."""
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(
                    f"File extension must start with dot: '{ext}' should be '.{ext}'"
                )
        return v

    def is_allowed_in_phase(self, phase: str) -> bool:
        """Check if operation allowed in given phase.

        Args:
            phase: Phase name to check

        Returns:
            True if operation allowed in phase, False otherwise
        """
        if not self.allowed_phases:  # Empty = all phases allowed
            return True
        return phase in self.allowed_phases

    def is_path_blocked(self, path: str) -> bool:
        """Check if path matches any blocked pattern.

        Args:
            path: File path to check (workspace-relative)

        Returns:
            True if path is blocked, False otherwise
        """
        for pattern in self.blocked_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def is_extension_allowed(self, path: str) -> bool:
        """Check if file extension is allowed.

        Args:
            path: File path to check

        Returns:
            True if extension allowed, False otherwise
        """
        if not self.allowed_extensions:  # Empty = all allowed
            return True

        ext = Path(path).suffix
        return ext in self.allowed_extensions

    def validate_commit_message(self, message: str) -> bool:
        """Check if commit message has valid TDD prefix.

        Args:
            message: Commit message to validate

        Returns:
            True if message valid or prefix not required, False otherwise
        """
        if not self.require_tdd_prefix:
            return True

        return any(message.startswith(prefix) for prefix in self.allowed_prefixes)


class OperationPoliciesConfig(BaseModel):
    """Operation policies configuration (WANNEER domain).

    Purpose: Define when operations are allowed (phase-based policies)
    Loaded from: .st3/policies.yaml
    Used by: PolicyEngine for operation decisions
    Cross-validates: allowed_phases against workflows.yaml
    """

    operations: Dict[str, OperationPolicy] = Field(
        ..., description="Operation policy definitions keyed by operation_id"
    )

    # Singleton pattern (ClassVar prevents Pydantic v2 ModelPrivateAttr bug)
    singleton_instance: ClassVar[Optional["OperationPoliciesConfig"]] = None

    @classmethod
    def from_file(
        cls, config_path: str = ".st3/policies.yaml"
    ) -> "OperationPoliciesConfig":
        """Load config from YAML file with cross-validation.

        Args:
            config_path: Path to policies.yaml file

        Returns:
            Singleton instance of OperationPoliciesConfig

        Raises:
            ConfigError: If file not found, YAML invalid, or cross-validation fails
        """
        # Return cached instance if exists
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        # Load and parse YAML
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}", file_path=config_path
            )

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path}: {e}", file_path=config_path
            ) from e

        # Validate structure
        if "operations" not in data:
            raise ConfigError(
                f"Missing 'operations' key in {config_path}",
                file_path=config_path,
            )

        # Transform to OperationPolicy instances
        operations = {}
        for op_id, op_data in data["operations"].items():
            try:
                operations[op_id] = OperationPolicy(operation_id=op_id, **op_data)
            except Exception as e:
                raise ConfigError(
                    f"Invalid operation policy for '{op_id}': {e}",
                    file_path=config_path,
                ) from e

        # Create instance
        instance = cls(operations=operations)

        # Cross-validation: Check allowed_phases exist in workflows.yaml
        instance._validate_phases()

        # Cache and return
        cls.singleton_instance = instance
        return cls.singleton_instance

    def _validate_phases(self) -> None:
        """Cross-validate allowed_phases against workflows.yaml.

        Raises:
            ConfigError: If any operation references unknown phase
        """
        # Collect all valid phases from all workflows
        valid_phases: set[str] = set()
        try:
            for wf_template in workflow_config.workflows.values():
                valid_phases.update(wf_template.phases)
        except Exception as e:
            raise ConfigError(
                f"Failed to load workflows.yaml for cross-validation: {e}",
                file_path=".st3/workflows.yaml",
            ) from e

        for op_id, policy in self.operations.items():
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
        if operation_id not in self.operations:
            raise ValueError(
                f"Unknown operation: '{operation_id}'. "
                f"Available operations: {sorted(self.operations.keys())}"
            )
        return self.operations[operation_id]

    def get_available_operations(self) -> List[str]:
        """Get list of all configured operation IDs.

        Returns:
            Sorted list of operation identifiers
        """
        return sorted(self.operations.keys())
