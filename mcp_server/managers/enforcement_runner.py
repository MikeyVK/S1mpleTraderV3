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

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.tool_result import ToolResult

_ENFORCEMENT_DISPLAY_PATH = ".st3/config/enforcement.yaml"


class EnforcementAction(BaseModel):
    """One configured enforcement action."""

    model_config = ConfigDict(extra="forbid")

    type: str
    policy: str | None = None
    rules: dict[str, list[str]] = Field(default_factory=dict)
    paths: list[str] = Field(default_factory=list)
    path: str | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> EnforcementAction:
        """Validate action-specific required fields."""
        if self.type == "check_branch_policy" and not self.rules:
            raise ValueError("check_branch_policy requires non-empty rules")
        if self.type == "commit_state_files" and not self.paths:
            raise ValueError("commit_state_files requires non-empty paths")
        if self.type == "delete_file" and not self.path:
            raise ValueError("delete_file requires path")
        return self


class EnforcementRule(BaseModel):
    """One configured enforcement rule."""

    model_config = ConfigDict(extra="forbid")

    event_source: str
    timing: str
    tool: str | None = None
    phase: str | None = None
    actions: list[EnforcementAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_target(self) -> EnforcementRule:
        """Validate rule target fields."""
        if self.event_source == "tool" and not self.tool:
            raise ValueError("tool event_source requires tool")
        if self.event_source == "phase" and not self.phase:
            raise ValueError("phase event_source requires phase")
        return self


class EnforcementConfig(BaseModel):
    """Typed root object for enforcement.yaml."""

    model_config = ConfigDict(extra="forbid")

    enforcement: list[EnforcementRule] = Field(default_factory=list)

    @classmethod
    def from_file(cls, file_path: Path) -> EnforcementConfig:
        """Load enforcement config from YAML.

        Missing config is treated as empty so existing workspaces remain usable.
        """
        if not file_path.exists():
            return cls()

        try:
            data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"Invalid YAML in {_ENFORCEMENT_DISPLAY_PATH}: {exc}",
                file_path=_ENFORCEMENT_DISPLAY_PATH,
            ) from exc

        try:
            return cls.model_validate(data)
        except PydanticValidationError as exc:
            raise ConfigError(
                f"Config validation failed for {_ENFORCEMENT_DISPLAY_PATH}: {exc}",
                file_path=_ENFORCEMENT_DISPLAY_PATH,
            ) from exc


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

    @classmethod
    def from_workspace(cls, workspace_root: Path | str) -> EnforcementRunner:
        """Create a runner from one workspace root."""
        root = Path(workspace_root)
        config = EnforcementConfig.from_file(root / _ENFORCEMENT_DISPLAY_PATH)
        return cls(workspace_root=root, config=config)

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

    @staticmethod
    def _build_default_registry() -> EnforcementRegistry:
        """Build the default action registry."""
        registry = EnforcementRegistry()
        registry.register(
            "check_branch_policy",
            EnforcementRunner._handle_check_branch_policy,
        )
        registry.register(
            "commit_state_files",
            EnforcementRunner._handle_commit_state_files,
        )
        return registry

    @staticmethod
    def _handle_check_branch_policy(
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
    ) -> str | None:
        """Block invalid branch creation bases based on branch-type rules."""
        del workspace_root
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

    @staticmethod
    def _handle_commit_state_files(
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
    ) -> str | None:
        """Commit state files after a successful tool execution."""
        branch = context.get_param("branch")
        if not isinstance(branch, str) or not branch:
            git_manager = GitManager()
            if hasattr(git_manager, "get_current_branch"):
                branch = git_manager.get_current_branch()
            else:
                branch = git_manager.adapter.get_current_branch()
        if not isinstance(branch, str) or not branch:
            return None

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager,
        )
        state = state_engine.get_state(branch)
        cycle_number = state.current_cycle if state.current_phase == "implementation" else None
        commit_hash = GitManager().commit_with_scope(
            workflow_phase=state.current_phase,
            message=action.message or "persist state after phase transition",
            cycle_number=cycle_number,
            commit_type="chore",
            files=action.paths,
        )
        return f"Enforcement committed state files: {commit_hash[:7]}"
