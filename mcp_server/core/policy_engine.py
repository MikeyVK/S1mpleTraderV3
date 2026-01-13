# mcp_server/core/policy_engine.py
"""Policy decision engine (config-driven).

Purpose: Make policy decisions based on YAML configs (Issue #54)
Responsibility: Single source of policy enforcement
Used by: MCP tools for operation validation
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

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
    path: Optional[str] = None
    phase: Optional[str] = None
    directory_policy: Optional[ResolvedDirectoryPolicy] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PolicyEngine:
    """Policy decision engine (config-driven).

    Completely config-driven - no hardcoded rules.
    Delegates to OperationPoliciesConfig and DirectoryPolicyResolver.
    """

    def __init__(self, config_dir: str = ".st3"):
        """Initialize PolicyEngine with configs.

        Args:
            config_dir: Directory containing config files
        """
        self._config_dir = config_dir

        # Load configs (singleton pattern ensures single load)
        self._operation_config = OperationPoliciesConfig.from_file(
            f"{config_dir}/policies.yaml"
        )
        self._directory_resolver = DirectoryPolicyResolver()

        # Audit trail
        self._audit_trail: List[Dict[str, Any]] = []

    def decide(
        self,
        operation: str,
        path: Optional[str] = None,
        phase: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyDecision:
        """Make policy decision for operation.

        Decision Algorithm:
        1. Check operation-level phase policy (WANNEER)
        2. If path provided, check directory policy (WAAR)
        3. Combine results + provide reason
        4. Log to audit trail

        Args:
            operation: Operation identifier (scaffold, create_file, commit)
            path: File path (optional, for path-based policies)
            phase: Current phase (optional, for phase-based policies)
            context: Additional context (component_type, branch, etc.)

        Returns:
            PolicyDecision with allowed/blocked + reason
        """
        context = context or {}

        try:
            # Get operation policy
            op_policy = self._operation_config.get_operation_policy(operation)

            # Check phase policy
            if phase and not op_policy.is_allowed_in_phase(phase):
                decision = PolicyDecision(
                    allowed=False,
                    reason=f"Operation '{operation}' not allowed in phase '{phase}'. "
                           f"Allowed phases: {op_policy.allowed_phases or 'all'}",
                    operation=operation,
                    path=path,
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
            if operation == "commit":
                message = context.get("message", "")
                if not op_policy.validate_commit_message(message):
                    decision = PolicyDecision(
                        allowed=False,
                        reason=f"Commit message must start with TDD prefix. "
                               f"Valid: {op_policy.allowed_prefixes}",
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

    def get_audit_trail(self) -> List[Dict[str, Any]]:
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
        # Reload
        self._operation_config = OperationPoliciesConfig.from_file(
            f"{self._config_dir}/policies.yaml"
        )
        # DirectoryResolver loads ProjectStructureConfig internally

