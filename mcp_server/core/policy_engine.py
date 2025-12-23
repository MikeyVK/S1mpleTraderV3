# mcp_server/core/policy_engine.py
"""
PolicyEngine - Phase A.1: Strict policy enforcement for MCP operations.

This module implements the core policy engine that validates all MCP operations
against project phase plans with NO backward compatibility (strict enforcement).

@layer: Core
@dependencies: []
"""

# Standard library
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Third-party

# Project modules


@dataclass
class DecisionContext:
    """Context for policy decisions."""
    operation: str  # "commit", "scaffold", "create_file", etc.
    branch: str
    project_plan: Any | None  # ProjectPlan or None
    phase: str  # Current phase being executed
    metadata: dict[str, Any]  # Operation-specific data


@dataclass
class PolicyDecision:
    """Result of a policy decision."""

    allowed: bool
    requires_human_approval: bool
    reason: str
    escalation_message: str | None = None


# pylint: disable=too-few-public-methods
class PolicyEngine:
    """Core policy enforcement engine with strict validation.

    NO opt-out mechanism - all operations must pass policy checks.
    """

    def __init__(self) -> None:
        """Initialize PolicyEngine with empty audit trail."""
        self.audit_trail: list[dict[str, Any]] = []

    def decide(self, ctx: DecisionContext) -> PolicyDecision:
        """Make a policy decision for the given context.

        Args:
            ctx: Decision context with operation, branch, project_plan, phase

        Returns:
            PolicyDecision with allowed flag and reason
        """
        # Validate project plan exists
        if ctx.project_plan is None:
            decision = PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason="No project plan found for branch",
                escalation_message="Branch must be initialized with project metadata"
            )
            self._log_audit(ctx, decision)
            return decision

        # Validate phase matches current_phase in project plan
        if ctx.phase != ctx.project_plan.current_phase:
            decision = PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason=f"Phase mismatch: operation phase '{ctx.phase}' != "
                       f"project current_phase '{ctx.project_plan.current_phase}'",
                escalation_message="Use TransitionPhaseTool to change phase first"
            )
            self._log_audit(ctx, decision)
            return decision

        # Validate phase is in required_phases
        if ctx.phase not in ctx.project_plan.required_phases:
            decision = PolicyDecision(
                allowed=False,
                requires_human_approval=True,
                reason=f"Phase '{ctx.phase}' not in required phases: "
                       f"{ctx.project_plan.required_phases}",
                escalation_message="Phase not planned for this issue type"
            )
            self._log_audit(ctx, decision)
            return decision

        # Delegate to operation-specific decision logic
        if ctx.operation == "commit":
            decision = self._decide_commit(ctx)
        elif ctx.operation == "scaffold":
            decision = self._decide_scaffold(ctx)
        elif ctx.operation == "create_file":
            decision = self._decide_create_file(ctx)
        else:
            # Unknown operation - allow with warning
            decision = PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason=f"Valid operation (phase validated): {ctx.operation}"
            )

        self._log_audit(ctx, decision)
        return decision

    def _decide_commit(self, ctx: DecisionContext) -> PolicyDecision:
        """Decide on git commit operations.

        Enforces TDD phase prefixes: red/green/refactor/docs
        """
        message = ctx.metadata.get("message", "")
        tdd_prefixes = ("red:", "green:", "refactor:", "docs:")

        if any(message.startswith(prefix) for prefix in tdd_prefixes):
            return PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason=f"Valid commit: TDD phase prefix found in '{message}'"
            )

        return PolicyDecision(
            allowed=False,
            requires_human_approval=True,
            reason="Missing TDD phase prefix (red:/green:/refactor:/docs:)",
            escalation_message="Commits must follow TDD workflow naming"
        )

    def _decide_scaffold(self, ctx: DecisionContext) -> PolicyDecision:
        """Decide on scaffold operations.

        Allows scaffolding in component/tdd phases only.
        """
        allowed_phases = {"component", "tdd"}

        if ctx.phase in allowed_phases:
            return PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason=f"Scaffolding allowed in {ctx.phase} phase"
            )

        return PolicyDecision(
            allowed=False,
            requires_human_approval=True,
            reason=f"Scaffolding not allowed in {ctx.phase} phase",
            escalation_message="Scaffold only in component/tdd phases"
        )

    def _decide_create_file(self, ctx: DecisionContext) -> PolicyDecision:
        """Decide on file creation operations.

        Path-based enforcement:
        - BLOCKED: backend/**/*.py, tests/**/*.py (must use scaffold)
        - ALLOWED: *.yml, *.json, *.toml, scripts/**, proof_of_concepts/**
        """
        path = Path(ctx.metadata.get("path", ""))

        # Check if path is blocked (must use scaffold)
        blocked_patterns = [
            ("backend", ".py"),
            ("tests", ".py"),
            ("mcp_server", ".py"),
        ]

        for dir_prefix, extension in blocked_patterns:
            if str(path).startswith(dir_prefix) and path.suffix == extension:
                return PolicyDecision(
                    allowed=False,
                    requires_human_approval=True,
                    reason=f"Python files in {dir_prefix}/ must use scaffold tool",
                    escalation_message="Use ScaffoldComponentTool instead of create_file"
                )

        # Check if path is explicitly allowed
        allowed_extensions = {".yml", ".yaml", ".json", ".toml", ".ini", ".txt", ".md", ".lock"}
        allowed_dirs = {"scripts", "proof_of_concepts", "docs", "config", ".st3"}

        if path.suffix in allowed_extensions:
            return PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason=f"Config file allowed: {path.suffix}"
            )

        if any(str(path).startswith(allowed_dir) for allowed_dir in allowed_dirs):
            return PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason=f"File allowed in {path.parts[0]}/ directory"
            )

        # Unknown file type - require approval
        return PolicyDecision(
            allowed=False,
            requires_human_approval=True,
            reason=f"Unknown file type: {path}",
            escalation_message="Unclear if this file should use scaffold"
        )

    def _log_audit(self, ctx: DecisionContext, decision: PolicyDecision) -> None:
        """Log decision to audit trail."""
        self.audit_trail.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": ctx.operation,
            "branch": ctx.branch,
            "phase": ctx.phase,
            "project_plan": {
                "issue_number": ctx.project_plan.issue_number if ctx.project_plan else None,
                "current_phase": ctx.project_plan.current_phase if ctx.project_plan else None,
            },
            "metadata": ctx.metadata,
            "decision": {
                "allowed": decision.allowed,
                "requires_human_approval": decision.requires_human_approval,
                "reason": decision.reason,
            },
        })
