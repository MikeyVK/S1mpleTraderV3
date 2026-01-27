# mcp_server/core/policy_engine.py
"""Policy decision engine (config-driven).

Purpose: Make policy decisions based on YAML configs (Issue #54)
Responsibility: Single source of policy enforcement
Used by: MCP tools for operation validation
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mcp_server.config.git_config import GitConfig
from mcp_server.config.operation_policies import OperationPoliciesConfig
from mcp_server.core.directory_policy_resolver import (
    DirectoryPolicyResolver,
    ResolvedDirectoryPolicy,
)


@dataclass
class PolicyDecision:
    """Result of a policy decision."""

    allowed: bool
    reason: str
    operation: str
    path: str | None = None
    phase: str | None = None
    directory_policy: ResolvedDirectoryPolicy | None = None
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PolicyEngine:
    """Policy decision engine (config-driven).

    Completely config-driven - no hardcoded rules.
    Delegates to OperationPoliciesConfig and DirectoryPolicyResolver.
    """

    def __init__(
        self,
        config_dir: str = ".st3",
        git_config: GitConfig | None = None
    ) -> None:
        """Initialize PolicyEngine with configs.

        Args:
            config_dir: Directory containing config files
            git_config: Optional GitConfig (for testing), defaults to singleton
        """
        self._config_dir = config_dir

        # Load configs (singleton pattern ensures single load)
        self._operation_config = OperationPoliciesConfig.from_file(
            f"{config_dir}/policies.yaml"
        )
        self._directory_resolver = DirectoryPolicyResolver()
        self._git_config = git_config or GitConfig.from_file()

        # Audit trail
        self._audit_trail: list[dict[str, Any]] = []

    def decide(
        self,
        operation: str,
        path: str | None = None,
        phase: str | None = None,
        context: dict[str, Any] | None = None
    ) -> PolicyDecision:
        """Make policy decision for operation.

        Decision Algorithm:
        1. Check operation-level phase policy (WANNEER)
        2. If path provided, check directory policy (WAAR)
        3. Combine results + provide reason

        Args:
            operation: Operation ID (scaffold, create_file, commit)
            path: Optional file path (for path-based policies)
            phase: Optional workflow phase (for phase-based policies)
            context: Optional context data (e.g., commit message)

        Returns:
            PolicyDecision with allowed/denied + reason
        """
        context = context or {}

        try:
            # Get operation policy
            op_policy = self._operation_config.get_operation_policy(operation)

            # Check phase (if specified)
            if phase and not op_policy.is_allowed_in_phase(phase):
                decision = PolicyDecision(
                    allowed=False,
                    reason=f"Operation '{operation}' not allowed in phase '{phase}'. "
                           f"Allowed phases: {op_policy.allowed_phases or 'all'}",
                    operation=operation,
                    phase=phase,
                    context=context
                )
                self._log_decision(decision)
                return decision

            # Check path-based policies (if path provided)
            if path:
                # Delegate to DirectoryPolicyResolver (SRP)
                dir_policy = self._directory_resolver.resolve(path)

                # Check component type (if provided in context)
                component_type = context.get("component_type")
                if component_type and not dir_policy.allows_component_type(
                    component_type
                ):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Component type '{component_type}' not allowed in "
                               f"'{dir_policy.path}'. Allowed types: "
                               f"{dir_policy.allowed_component_types or 'all'}",
                        operation=operation,
                        path=path,
                        phase=phase,
                        directory_policy=dir_policy,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision

                # Check blocked patterns (create_file operation)
                if operation == "create_file" and op_policy.is_path_blocked(path):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Path '{path}' matches blocked pattern. "
                               "Must use scaffold operation instead.",
                        operation=operation,
                        path=path,
                        phase=phase,
                        directory_policy=dir_policy,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision

                # Check allowed extensions (create_file operation)
                if operation == "create_file" and not op_policy.is_extension_allowed(
                    path
                ):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"File extension not allowed. "
                               f"Allowed: {op_policy.allowed_extensions or 'all'}",
                        operation=operation,
                        path=path,
                        phase=phase,
                        directory_policy=dir_policy,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision

            # Check commit message (commit operation)
            # Convention #6: Use GitConfig-derived prefixes instead of hardcoded list
            if operation == "commit" and op_policy.require_tdd_prefix:
                message = context.get("message", "")
                valid_prefixes = self._git_config.get_all_prefixes()

                if not any(message.startswith(prefix) for prefix in valid_prefixes):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Commit message must start with TDD prefix. "
                               f"Valid: {valid_prefixes}",
                        operation=operation,
                        phase=phase,
                        context=context
                    )
                    self._log_decision(decision)
                    return decision

            # All checks passed - operation allowed
            decision = PolicyDecision(
                allowed=True,
                reason=f"Operation '{operation}' allowed in phase '{phase or 'any'}'"
                       + (f" for path '{path}'" if path else ""),
                operation=operation,
                path=path,
                phase=phase,
                directory_policy=self._directory_resolver.resolve(path) if path else None,
                context=context
            )
            self._log_decision(decision)
            return decision

        except Exception as e:
            # Error in policy evaluation - log and deny by default (fail-safe)
            decision = PolicyDecision(
                allowed=False,
                reason=f"Policy evaluation error: {e}",
                operation=operation,
                path=path,
                phase=phase,
                context=context
            )
            self._log_decision(decision)
            return decision

    def _log_decision(self, decision: PolicyDecision) -> None:
        """Log decision to audit trail."""
        self._audit_trail.append({
            "timestamp": decision.timestamp.isoformat(),
            "operation": decision.operation,
            "path": decision.path,
            "phase": decision.phase,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "context": decision.context
        })

    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Get complete audit trail.

        Returns:
            List of all policy decisions with metadata
        """
        return list(self._audit_trail)

    def reload_configs(self) -> None:
        """Reload configs from disk (without restart).

        Useful for testing and dynamic config updates.
        """
        # Reset singleton instances
        OperationPoliciesConfig.reset_instance()
        GitConfig.reset_instance()
        # Reload
        self._operation_config = OperationPoliciesConfig.from_file(
            f"{self._config_dir}/policies.yaml"
        )
        self._git_config = GitConfig.from_file()
        # DirectoryResolver loads ProjectStructureConfig internally
