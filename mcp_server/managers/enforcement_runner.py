# mcp_server/managers/enforcement_runner.py
# template=generic version=manual-cycle5 created=2026-03-13T11:20Z updated=
"""Enforcement configuration loading and dispatch.

Dispatch-level enforcement runner for tool events configured in
.st3/config/enforcement.yaml.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import cast

from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.schemas import EnforcementAction, EnforcementConfig, EnforcementRule
from mcp_server.tools.tool_result import ToolResult

_ENFORCEMENT_DISPLAY_PATH = ".st3/config/enforcement.yaml"

__all__ = [
    "EnforcementAction",
    "EnforcementConfig",
    "EnforcementContext",
    "EnforcementRule",
    "EnforcementRunner",
]


@dataclass(frozen=True)
class EnforcementContext:
    """Runtime context passed to action handlers."""

    workspace_root: Path
    tool_name: str
    params: object
    tool_result: ToolResult | None = None

    def get_param(self, name: str) -> object | None:
        """Read one parameter from Pydantic models, namespaces, or dicts."""
        if hasattr(self.params, name):
            return cast(object, getattr(self.params, name))
        if isinstance(self.params, dict):
            return self.params.get(name)
        return None


ActionHandler = Callable[[EnforcementAction, EnforcementContext, Path], str | None]


class EnforcementRegistry:
    """Registry for named enforcement action handlers."""

    def __init__(self, handlers: dict[str, ActionHandler] | None = None) -> None:
        self._handlers = handlers or {}

    def register(self, action_type: str, handler: ActionHandler) -> None:
        """Register one action handler."""
        self._handlers[action_type] = handler

    def has(self, action_type: str) -> bool:
        """Check whether one action type is registered."""
        return action_type in self._handlers

    def get(self, action_type: str) -> ActionHandler:
        """Get one registered action handler."""
        return self._handlers[action_type]


class EnforcementRunner:
    """Load and execute enforcement rules for tool events."""

    def __init__(
        self,
        workspace_root: Path,
        config: EnforcementConfig,
        registry: EnforcementRegistry | dict[str, ActionHandler] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self._config = config
        if registry is None:
            self._registry = self._build_default_registry()
        elif isinstance(registry, EnforcementRegistry):
            self._registry = registry
        else:
            self._registry = EnforcementRegistry(registry)
        self._validate_registered_actions()

    def run(self, event: str, timing: str, context: EnforcementContext) -> list[str]:
        """Execute matching actions for one event and timing pair."""
        notes: list[str] = []
        for rule in self._config.enforcement:
            if rule.event_source != "tool":
                continue
            if rule.tool != event or rule.timing != timing:
                continue
            for action in rule.actions:
                note = self._registry.get(action.type)(action, context, self.workspace_root)
                if note:
                    notes.append(note)
        return notes

    def _validate_registered_actions(self) -> None:
        """Fail fast when config references unknown action types."""
        unknown = sorted(
            {
                action.type
                for rule in self._config.enforcement
                for action in rule.actions
                if not self._registry.has(action.type)
            }
        )
        if unknown:
            raise ConfigError(
                f"Unknown enforcement action type(s): {', '.join(unknown)}",
                file_path=_ENFORCEMENT_DISPLAY_PATH,
            )

    def _build_default_registry(self) -> EnforcementRegistry:
        """Build the default action registry."""
        registry = EnforcementRegistry()
        registry.register(
            "check_branch_policy",
            self._handle_check_branch_policy,
        )
        return registry

    def _handle_check_branch_policy(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
    ) -> str | None:
        """Block invalid branch creation bases based on branch-type rules."""
        del self, workspace_root
        branch_type = context.get_param("branch_type")
        base_branch = context.get_param("base_branch")
        if not branch_type or not base_branch:
            return None

        allowed_patterns = action.rules.get(str(branch_type), [])
        if not allowed_patterns:
            return None

        if any(fnmatch(str(base_branch), pattern) for pattern in allowed_patterns):
            return None

        raise ValidationError(
            f"Branch type '{branch_type}' cannot be created from base '{base_branch}'",
            hints=[f"Allowed bases: {', '.join(allowed_patterns)}"],
        )
