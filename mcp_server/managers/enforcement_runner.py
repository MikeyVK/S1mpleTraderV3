# mcp_server/managers/enforcement_runner.py
# template=generic version=manual-cycle5 created=2026-03-13T11:20Z updated=
"""Enforcement configuration loading and dispatch.

Dispatch-level enforcement runner for tool events configured in
.st3/config/enforcement.yaml.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import cast

from mcp_server.core.exceptions import ConfigError, ExecutionError, ValidationError
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.schemas import EnforcementAction, EnforcementConfig, EnforcementRule
from mcp_server.tools.tool_result import ToolResult

_ENFORCEMENT_DISPLAY_PATH = ".st3/config/enforcement.yaml"


def _read_current_phase(workspace_root: Path) -> str | None:
    """Read the current workflow phase from .st3/state.json at call time."""
    state_file = workspace_root / ".st3" / "state.json"
    if not state_file.exists():
        return None
    data: dict[str, object] = json.loads(state_file.read_text(encoding="utf-8"))
    raw = data.get("current_phase")
    return str(raw) if raw else None


def _git_is_tracked(workspace_root: Path, path: str) -> bool:
    """Return True if *path* is currently tracked in the git index."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=workspace_root,
        capture_output=True,
    )
    return result.returncode == 0


def _git_rm_cached(workspace_root: Path, path: str) -> None:
    """Remove *path* from the git index without deleting the working-tree file."""
    result = subprocess.run(
        ["git", "rm", "--cached", "--ignore-unmatch", path],
        cwd=workspace_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        raise ExecutionError(
            f"git rm --cached failed for '{path}': {stderr}",
            recovery=[
                "Run `git status` to inspect the index state",
                "Manually run: git rm --cached <path>",
                f"Check that the file exists and is tracked: git ls-files {path}",
            ],
        )


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
        merge_readiness_context: MergeReadinessContext | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self._config = config
        self._merge_readiness_context = merge_readiness_context
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
        registry.register(
            "exclude_branch_local_artifacts",
            self._handle_exclude_branch_local_artifacts,
        )
        registry.register(
            "check_merge_readiness",
            self._handle_check_merge_readiness,
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

    def _handle_exclude_branch_local_artifacts(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
    ) -> str | None:
        """Auto-exclude configured branch-local artifacts from the commit index.

        Only runs when the current workflow phase equals the configured terminal phase.
        For each artifact in merge_readiness_context.branch_local_artifacts that is
        git-tracked, runs ``git rm --cached`` and returns a formatted exclusion note.
        """
        del action, context
        if self._merge_readiness_context is None:
            return None
        ctx = self._merge_readiness_context

        current_phase = _read_current_phase(workspace_root)
        if current_phase != ctx.terminal_phase:
            return None

        excluded = [
            artifact
            for artifact in ctx.branch_local_artifacts
            if _git_is_tracked(workspace_root, artifact.path)
        ]
        if not excluded:
            return None

        for artifact in excluded:
            _git_rm_cached(workspace_root, artifact.path)

        lines = ["Branch-local artifacts excluded from commit index:"]
        for artifact in excluded:
            lines.append(f"  - {artifact.path}")
            lines.append(f"    Reason: {artifact.reason}")
        lines.append("")
        lines.append(
            "Source: .st3/config/phase_contracts.yaml → merge_policy.branch_local_artifacts"
        )
        return "\n".join(lines)

    def _handle_check_merge_readiness(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
    ) -> str | None:
        """Block PR creation when phase or tracked-artifact checks fail.

        Check 1 — Phase gate: current_phase must equal pr_allowed_phase.
        Check 2 — Artifact pre-flight: no branch-local artifact may remain git-tracked.
        Both checks read live state at handler execution time.
        """
        del action, context
        if self._merge_readiness_context is None:
            return None
        ctx = self._merge_readiness_context

        # Check 1 — Phase gate (read live from state.json)
        current_phase = _read_current_phase(workspace_root)
        if current_phase != ctx.pr_allowed_phase:
            raise ValidationError(
                f"PR creation requires phase '{ctx.pr_allowed_phase}'. "
                f"Current phase: '{current_phase}'.",
                hints=[f'transition_phase(to_phase="{ctx.pr_allowed_phase}")'],
            )

        # Check 2 — Artifact pre-flight
        tracked = [
            artifact
            for artifact in ctx.branch_local_artifacts
            if _git_is_tracked(workspace_root, artifact.path)
        ]
        if tracked:
            artifact_hints = [f"  - {a.path}\n    Reason: {a.reason}" for a in tracked]
            raise ValidationError(
                "Branch-local artifacts are still git-tracked and would contaminate main:",
                hints=[
                    *artifact_hints,
                    "Commit first in the ready phase to auto-exclude them:",
                    '  git_add_or_commit(message="chore: prepare branch for PR")',
                    "Source: .st3/config/phase_contracts.yaml"
                    " → merge_policy.branch_local_artifacts",
                ],
            )
        return None
