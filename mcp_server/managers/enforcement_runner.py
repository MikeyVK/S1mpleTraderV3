# mcp_server/managers/enforcement_runner.py
# template=generic version=manual-cycle5 created=2026-03-13T11:20Z updated=
"""Enforcement configuration loading and dispatch.

Dispatch-level enforcement runner for tool events configured in
.st3/config/enforcement.yaml.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import cast

from mcp_server.core.exceptions import ConfigError, ExecutionError, ValidationError
from mcp_server.core.interfaces import IPRStatusReader, PRStatus
from mcp_server.core.operation_notes import (
    ExclusionNote,
    NoteContext,
    RecoveryNote,
    SuggestionNote,
)
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.schemas import EnforcementAction, EnforcementConfig, EnforcementRule
from mcp_server.tools.tool_result import ToolResult

_ENFORCEMENT_DISPLAY_PATH = ".st3/config/enforcement.yaml"
_GIT_TIMEOUT_SECONDS = 2
logger = logging.getLogger(__name__)

# Known tool_category values; config validation fails fast for any unlisted value.
KNOWN_TOOL_CATEGORIES: frozenset[str] = frozenset({"branch_mutating"})


def _read_current_phase(workspace_root: Path) -> str | None:
    """Read the current workflow phase from .st3/state.json at call time."""
    state_file = workspace_root / ".st3" / "state.json"
    if not state_file.exists():
        return None
    data: dict[str, object] = json.loads(state_file.read_text(encoding="utf-8"))
    raw = data.get("current_phase")
    return str(raw) if raw else None


def _git_command_env() -> dict[str, str]:
    """Build a non-interactive environment for git commands in request paths."""
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_PAGER", "cat")
    env.setdefault("PAGER", "cat")
    return env


def _run_git_command(
    workspace_root: Path,
    args: list[str],
    failure_context: str,
) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand non-interactively and return the CompletedProcess."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=workspace_root,
            env=_git_command_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("git command failed (%s): %s", failure_context, exc)
        return subprocess.CompletedProcess(
            args=["git", *args], returncode=1, stdout="", stderr=str(exc)
        )


def _git_is_tracked(workspace_root: Path, path: str) -> bool:
    """Return True if *path* is currently tracked in the git index."""
    result = _run_git_command(
        workspace_root,
        ["ls-files", "--error-unmatch", path],
        failure_context=f"git ls-files failed for '{path}'",
    )
    return result.returncode == 0


def _has_net_diff_for_path(workspace_root: Path, path: str, base: str) -> bool:
    """Return True if *path* has a net delta between the merge-base and HEAD.

    Uses ``git diff --name-only merge_base..HEAD -- path`` to determine whether
    this branch introduced any commits that modified *path* relative to *base*.

    Raises ExecutionError on non-zero git exit codes so callers receive an
    explicit signal rather than a silent false negative.
    """
    merge_base_result = _run_git_command(
        workspace_root,
        ["merge-base", "HEAD", base],
        failure_context=f"git merge-base failed for base='{base}'",
    )
    if merge_base_result.returncode != 0:
        raise ExecutionError(
            f"git merge-base failed for base='{base}': {merge_base_result.stderr.strip()}"
        )
    merge_base = merge_base_result.stdout.strip()

    diff_result = _run_git_command(
        workspace_root,
        ["diff", "--name-only", f"{merge_base}..HEAD", "--", path],
        failure_context=f"git diff failed for path='{path}'",
    )
    if diff_result.returncode != 0:
        raise ExecutionError(f"git diff failed for path='{path}': {diff_result.stderr.strip()}")
    return path in diff_result.stdout.splitlines()


def _git_rm_cached(workspace_root: Path, path: str, note_context: NoteContext) -> None:
    """Remove *path* from the git index without deleting the working-tree file."""
    result = _run_git_command(
        workspace_root,
        ["rm", "--cached", "--ignore-unmatch", path],
        failure_context=f"git rm --cached failed for '{path}'",
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        note_context.produce(
            RecoveryNote(message="Run 'git status' to inspect current index state")
        )
        note_context.produce(RecoveryNote(message=f"Manually run: git rm --cached {path}"))
        raise ExecutionError(f"git rm --cached failed for '{path}': {stderr}")


__all__ = [
    "EnforcementAction",
    "EnforcementConfig",
    "EnforcementContext",
    "EnforcementConfig",
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


ActionHandler = Callable[
    [EnforcementAction, EnforcementContext, Path, NoteContext],
    None,
]


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
        default_base_branch: str = "main",
        pr_status_reader: IPRStatusReader | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self._config = config
        self._merge_readiness_context = merge_readiness_context
        self.default_base_branch = default_base_branch
        self._pr_status_reader = pr_status_reader
        if registry is None:
            self._registry = self._build_default_registry()
        elif isinstance(registry, EnforcementRegistry):
            self._registry = registry
        else:
            self._registry = EnforcementRegistry(registry)
        self._validate_registered_actions()

    def run(
        self,
        event: str,
        timing: str,
        enforcement_ctx: EnforcementContext,
        note_context: NoteContext,
        tool_category: str | None = None,
    ) -> None:
        """Execute matching actions for one event and timing pair.

        C3: returns None; all results conveyed via note_context.produce().
        Dispatch matches on rule.tool (tool name) OR rule.tool_category (category).
        """
        for rule in self._config.enforcement:
            if rule.event_source != "tool":
                continue
            if rule.timing != timing:
                continue
            # Match by tool name or tool_category (mutually exclusive per schema validator)
            if rule.tool is not None and rule.tool != event:
                continue
            if rule.tool_category is not None and rule.tool_category != tool_category:
                continue
            if rule.tool is None and rule.tool_category is None:
                continue
            for action in rule.actions:
                self._registry.get(action.type)(
                    action, enforcement_ctx, self.workspace_root, note_context
                )

    def _validate_registered_actions(self) -> None:
        """Fail fast when config references unknown action types or tool categories."""
        unknown_actions = sorted(
            {
                action.type
                for rule in self._config.enforcement
                for action in rule.actions
                if not self._registry.has(action.type)
            }
        )
        if unknown_actions:
            raise ConfigError(
                f"Unknown enforcement action type(s): {', '.join(unknown_actions)}",
                file_path=_ENFORCEMENT_DISPLAY_PATH,
            )

        unknown_categories = sorted(
            {
                rule.tool_category
                for rule in self._config.enforcement
                if rule.tool_category is not None
                and rule.tool_category not in KNOWN_TOOL_CATEGORIES
            }
        )
        if unknown_categories:
            raise ConfigError(
                f"Unknown tool_category value(s): {', '.join(unknown_categories)}",
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
        registry.register(
            "check_pr_status",
            self._handle_check_pr_status,
        )
        registry.register(
            "check_phase_readiness",
            self._handle_check_phase_readiness,
        )
        return registry

    def _handle_check_branch_policy(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
        note_context: NoteContext,
    ) -> None:
        """Block invalid branch creation bases based on branch-type rules."""
        del self, workspace_root
        branch_type = context.get_param("branch_type")
        base_branch = context.get_param("base_branch")
        if not branch_type or not base_branch:
            return

        allowed_patterns = action.rules.get(str(branch_type), [])
        if not allowed_patterns:
            return

        if any(fnmatch(str(base_branch), pattern) for pattern in allowed_patterns):
            return

        note_context.produce(
            SuggestionNote(message=f"Allowed bases: {', '.join(allowed_patterns)}")
        )
        raise ValidationError(
            f"Branch type '{branch_type}' cannot be created from base '{base_branch}'",
        )

    def _handle_exclude_branch_local_artifacts(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
        note_context: NoteContext,
    ) -> None:
        """Write ExclusionNote for each confirmed-tracked branch-local artifact.

        Only runs when the current workflow phase equals the configured terminal phase.
        For each artifact in merge_readiness_context.branch_local_artifacts that is
        git-tracked, produces an ExclusionNote in note_context. No git operations.

        C3 contract: zero git ops in this handler. GitAdapter.commit(skip_paths=)
        owns the actual exclusion from the staging area.
        """
        del action, context
        if self._merge_readiness_context is None:
            return
        ctx = self._merge_readiness_context

        current_phase = _read_current_phase(workspace_root)
        if current_phase != ctx.terminal_phase:
            return

        for artifact in ctx.branch_local_artifacts:
            if not _git_is_tracked(workspace_root, artifact.path):
                continue
            note_context.produce(ExclusionNote(file_path=artifact.path))

    def _handle_check_merge_readiness(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
        note_context: NoteContext,
    ) -> None:
        """Block PR creation when phase or net-diff-artifact checks fail.

        Check 1 — Phase gate: current_phase must equal pr_allowed_phase.
        Check 2 — Artifact net-diff pre-flight: no branch-local artifact may have
          a net delta between the merge-base and HEAD. Uses _has_net_diff_for_path
          (git diff merge_base..HEAD) rather than _git_is_tracked (git ls-files)
          to avoid false positives when the artifact is inherited from the base branch.
        Both checks read live state at handler execution time.
        """
        del action  # action config not used; context MUST remain live for get_param()
        if self._merge_readiness_context is None:
            return
        ctx = self._merge_readiness_context

        base = str(context.get_param("base") or self.default_base_branch)

        # Check 1 — Phase gate (read live from state.json)
        current_phase = _read_current_phase(workspace_root)
        if current_phase != ctx.pr_allowed_phase:
            note_context.produce(
                SuggestionNote(message=f'transition_phase(to_phase="{ctx.pr_allowed_phase}")')
            )
            raise ValidationError(
                f"PR creation requires phase '{ctx.pr_allowed_phase}'. "
                f"Current phase: '{current_phase}'.",
            )

        # Check 2 — Artifact net-diff pre-flight (C6: replaces _git_is_tracked)
        tracked = [
            artifact
            for artifact in ctx.branch_local_artifacts
            if _has_net_diff_for_path(workspace_root, artifact.path, base)
        ]
        if tracked:
            for a in tracked:
                note_context.produce(
                    SuggestionNote(message=f"  - {a.path}\n    Reason: {a.reason}")
                )
            note_context.produce(
                SuggestionNote(
                    message=f"Run git_add_or_commit in phase '{ctx.pr_allowed_phase}'"
                    f" to neutralize these paths:"
                )
            )
            note_context.produce(
                SuggestionNote(
                    message=f'  git_add_or_commit(workflow_phase="{ctx.pr_allowed_phase}",'
                    ' message="...")'
                )
            )
            note_context.produce(
                SuggestionNote(
                    message=f"  This commit will align the branch tip to '{base}'"
                    " for the excluded paths."
                )
            )
            raise ValidationError(
                f"Branch-local artifacts have a net delta against '{base}' and"
                " would contaminate the merge target:",
            )

    def _handle_check_pr_status(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
        note_context: NoteContext,
    ) -> None:
        """Block branch-mutating tool calls when an open PR exists for this branch.

        Reads IPRStatusReader (session-leading cache, cold-start API fallback).
        Raises ConfigError when no reader is configured (misconfigured startup).
        Raises ValidationError when PRStatus.OPEN is found.
        """
        del action, workspace_root
        if self._pr_status_reader is None:
            raise ConfigError(
                "check_pr_status action requires pr_status_reader; "
                "wire PRStatusCache in EnforcementRunner.__init__",
                file_path=_ENFORCEMENT_DISPLAY_PATH,
            )
        # Use the 'head' param if available, fall back to tool_name as branch identifier.
        branch = str(context.get_param("head") or context.tool_name)
        status = self._pr_status_reader.get_pr_status(branch)
        if status == PRStatus.OPEN:
            note_context.produce(
                SuggestionNote(
                    message="Call merge_pr to close the open PR before continuing branch work."
                )
            )
            raise ValidationError(
                f"Branch '{branch}' has an open PR. "
                "Branch-mutating tools are blocked until the PR is merged.",
            )

    def _handle_check_phase_readiness(
        self,
        action: EnforcementAction,
        context: EnforcementContext,
        workspace_root: Path,
        note_context: NoteContext,
    ) -> None:
        """Block tool execution when the current workflow phase does not match policy.

        Reads action.policy as the required phase name; compares against
        live state.json. Raises ValidationError on mismatch or absent state.
        """
        del context
        required_phase = action.policy
        current_phase = _read_current_phase(workspace_root)
        if current_phase != required_phase:
            note_context.produce(
                SuggestionNote(
                    message=f'transition_phase(to_phase="{required_phase}")'
                )
            )
            raise ValidationError(
                f"Tool requires phase '{required_phase}'. "
                f"Current phase: '{current_phase}'.",
            )
