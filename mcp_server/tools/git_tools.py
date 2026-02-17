"""Git tools."""

import subprocess
from pathlib import Path
from typing import Any

import anyio
from pydantic import BaseModel, Field, field_validator, model_validator

from mcp_server.config.git_config import GitConfig
from mcp_server.core.exceptions import MCPError
from mcp_server.core.logging import get_logger
from mcp_server.managers import phase_state_engine, project_manager
from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

logger = get_logger("tools.git")


def _input_schema(args_model: type[BaseModel] | None) -> dict[str, Any]:
    if args_model is None:
        return {}
    return args_model.model_json_schema()


class CreateBranchInput(BaseModel):
    """Input for CreateBranchTool."""

    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(default="feature", description="Branch type")
    base_branch: str = Field(
        ...,
        description="Base branch to create from (e.g., 'HEAD', 'main', 'refactor/51-labels-yaml')",
    )

    @field_validator("branch_type")
    @classmethod
    def validate_branch_type(cls, value: str) -> str:
        """Validate branch_type against GitConfig (Convention #7)."""
        git_config = GitConfig.from_file()
        if not git_config.has_branch_type(value):
            valid_types = ", ".join(git_config.branch_types)
            raise ValueError(
                f"Invalid branch_type '{value}'. Valid types from git.yaml: {valid_types}"
            )
        return value


class CreateBranchTool(BaseTool):
    """Tool to create a git branch from specified base."""

    name = "create_branch"
    description = "Create a new branch from specified base branch"
    args_model = CreateBranchInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: CreateBranchInput) -> ToolResult:
        logger.info(
            "Branch creation requested",
            extra={
                "props": {
                    "name": params.name,
                    "branch_type": params.branch_type,
                    "base_branch": params.base_branch,
                }
            },
        )

        try:
            branch_name = self.manager.create_branch(
                params.name, params.branch_type, params.base_branch
            )
            return ToolResult.text(f"âœ… Created and switched to branch: {branch_name}")
        except Exception as e:
            logger.error(
                "Branch creation failed", extra={"props": {"name": params.name, "error": str(e)}}
            )
            raise


class GitStatusInput(BaseModel):
    """Input for GitStatusTool (empty)."""


class GitStatusTool(BaseTool):
    """Tool to check git status."""

    name = "git_status"
    description = "Check current git status"
    args_model = GitStatusInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitStatusInput) -> ToolResult:  # noqa: ARG002
        status = self.manager.get_status()

        text = f"Branch: {status['branch']}\n"
        text += f"Clean: {status['is_clean']}\n"
        if status["untracked_files"]:
            text += f"Untracked: {', '.join(status['untracked_files'])}\n"
        if status["modified_files"]:
            text += f"Modified: {', '.join(status['modified_files'])}\n"

        return ToolResult.text(text)


class GitCommitInput(BaseModel):
    """Input for GitCommitTool."""

    message: str = Field(..., description="Commit message (without type/scope prefix)")
    files: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of file paths to stage and commit. When omitted, commits all changes."
        ),
    )

    # NEW: Workflow-first fields
    workflow_phase: str | None = Field(
        default=None,
        description=(
            "Workflow phase (research|planning|design|tdd|integration|documentation|coordination). "
            "Required when using new workflow-first format."
        ),
    )
    sub_phase: str | None = Field(
        default=None,
        description=(
            "Sub-phase (MUST be in workphases.yaml[phase].subphases). "
            "Examples: 'red', 'green', 'c1'. Optional."
        ),
    )
    cycle_number: int | None = Field(
        default=None,
        description="Cycle number (e.g., 1, 2, 3). Optional, used in multi-cycle TDD.",
    )
    commit_type: str | None = Field(
        default=None,
        description=(
            "Commit type override (test|feat|refactor|docs|chore|fix). "
            "Auto-determined from workphases.yaml if omitted."
        ),
    )

    # DEPRECATED: Backward compatibility
    phase: str | None = Field(
        default=None,
        description=(
            "DEPRECATED: TDD phase (red=test, green=feat, refactor, docs). "
            "Use workflow_phase + sub_phase instead."
        ),
    )

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, value: str | None) -> str | None:
        """Validate phase against GitConfig (Convention #8). Only if provided."""
        if value is None:
            return None
        git_config = GitConfig.from_file()
        if not git_config.has_phase(value):
            valid_phases = ", ".join(git_config.tdd_phases)
            raise ValueError(f"Invalid phase '{value}'. Valid phases from git.yaml: {valid_phases}")
        return value

    @field_validator("commit_type")
    @classmethod
    def validate_commit_type(cls, value: str | None) -> str | None:
        """Validate commit_type against GitConfig (Convention #6). Only if provided."""
        if value is None:
            return None

        git_config = GitConfig.from_file()
        if not git_config.has_commit_type(value):
            valid_types = ", ".join(git_config.commit_types)
            raise ValueError(
                f"Invalid commit_type '{value}'. "
                f"Valid types from git.yaml: {valid_types}. "
                f"See: https://www.conventionalcommits.org/"
            )

        return value.lower()  # Normalize to lowercase

    @model_validator(mode="after")
    def validate_phase_or_workflow_phase(self) -> "GitCommitInput":
        """Ensure phase and workflow_phase are not both specified.

        Auto-detection: If neither is provided, workflow_phase will be auto-detected
        from state.json in execute() method.
        """
        has_phase = self.phase is not None
        has_workflow = self.workflow_phase is not None

        if has_phase and has_workflow:
            raise ValueError(
                "Cannot specify both 'phase' (deprecated) and 'workflow_phase'. "
                "Use workflow_phase only."
            )

        return self


class GitCommitTool(BaseTool):
    """Tool to commit changes with workflow-scoped commit messages."""

    name = "git_add_or_commit"
    description = "Commit changes with workflow phase scope (e.g., test(P_TDD_SP_RED): message)"
    args_model = GitCommitInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitCommitInput) -> ToolResult:
        # Auto-detect workflow_phase from state.json if not provided
        workflow_phase = params.workflow_phase
        if workflow_phase is None and params.phase is None:
            # Get current branch
            current_branch = self.manager.adapter.get_current_branch()

            # Read workflow_phase from state.json
            workspace_root = Path.cwd()
            pm = project_manager.ProjectManager(workspace_root=workspace_root)
            state_engine = phase_state_engine.PhaseStateEngine(
                workspace_root=workspace_root,
                project_manager=pm,
            )
            workflow_phase = state_engine.get_current_phase(branch=current_branch)

            logger.info(
                "Auto-detected workflow_phase from state.json",
                extra={"props": {"branch": current_branch, "workflow_phase": workflow_phase}},
            )

        # NEW workflow-first path
        if workflow_phase is not None:
            commit_hash = self.manager.commit_with_scope(
                workflow_phase=workflow_phase,
                message=params.message,
                sub_phase=params.sub_phase,
                cycle_number=params.cycle_number,
                commit_type=params.commit_type,
                files=params.files,
            )
        # LEGACY backward-compatible path (phase -> workflow mapping)
        else:
            legacy_phase = params.phase
            if legacy_phase == "docs":
                mapped_workflow_phase = "documentation"
                mapped_sub_phase = None
            else:
                mapped_workflow_phase = "tdd"
                mapped_sub_phase = legacy_phase

            commit_hash = self.manager.commit_with_scope(
                workflow_phase=mapped_workflow_phase,
                message=params.message,
                sub_phase=mapped_sub_phase,
                cycle_number=params.cycle_number,
                commit_type=params.commit_type,
                files=params.files,
            )
        return ToolResult.text(f"Committed: {commit_hash}")


class GitRestoreInput(BaseModel):
    """Input for GitRestoreTool."""

    files: list[str] = Field(
        ..., min_length=1, description="File paths to restore (discard local changes)"
    )
    source: str = Field(default="HEAD", description="Git ref to restore from (default: HEAD)")


class GitRestoreTool(BaseTool):
    """Tool to restore files to a ref (discard local changes)."""

    name = "git_restore"
    description = "Restore files to a git ref (discard local changes)"
    args_model = GitRestoreInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitRestoreInput) -> ToolResult:
        self.manager.restore(files=params.files, source=params.source)
        return ToolResult.text(f"Restored {len(params.files)} file(s) from {params.source}")


class GitCheckoutInput(BaseModel):
    """Input for GitCheckoutTool."""

    branch: str = Field(..., description="Branch name to checkout")


class GitCheckoutTool(BaseTool):
    """Tool to checkout to a branch.

    Automatically synchronizes PhaseStateEngine state after branch switch
    to ensure correct TDD phase tracking.
    """

    name = "git_checkout"
    description = "Switch to an existing branch"
    args_model = GitCheckoutInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitCheckoutInput) -> ToolResult:
        workspace_root = Path.cwd()

        try:
            # GitPython operations can block; run them in a worker thread.
            await anyio.to_thread.run_sync(self.manager.checkout, params.branch)
        except MCPError as exc:
            logger.error(
                "Branch checkout failed",
                extra={"props": {"branch": params.branch, "error": str(exc)}},
            )
            return ToolResult.error(str(exc))

        current_phase = "unknown"
        state: dict[str, Any] = {}
        try:
            pm = project_manager.ProjectManager(workspace_root=workspace_root)
            engine = phase_state_engine.PhaseStateEngine(
                workspace_root=workspace_root,
                project_manager=pm,
            )
            state = await anyio.to_thread.run_sync(engine.get_state, params.branch)
            current_phase = state.get("current_phase") or "unknown"
        except (MCPError, ValueError, OSError) as exc:
            logger.warning(
                "Phase state sync failed after checkout",
                extra={"props": {"branch": params.branch, "error": str(exc)}},
            )

        parent_branch = state.get("parent_branch") if "state" in locals() else None

        output = f"Switched to branch: {params.branch}\nCurrent phase: {current_phase}"
        if parent_branch:
            output += f"\nParent branch: {parent_branch}"

        return ToolResult.text(output)


class GitPushInput(BaseModel):
    """Input for GitPushTool."""

    set_upstream: bool = Field(
        default=False, description="Set upstream tracking (for new branches)"
    )


class GitPushTool(BaseTool):
    """Tool to push current branch to origin."""

    name = "git_push"
    description = "Push current branch to origin remote"
    args_model = GitPushInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitPushInput) -> ToolResult:
        status = self.manager.get_status()
        self.manager.push(set_upstream=params.set_upstream)
        return ToolResult.text(f"Pushed branch: {status['branch']}")


class GitMergeInput(BaseModel):
    """Input for GitMergeTool."""

    branch: str = Field(..., description="Branch name to merge")


class GitMergeTool(BaseTool):
    """Tool to merge a branch into current branch."""

    name = "git_merge"
    description = "Merge a branch into the current branch"
    args_model = GitMergeInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitMergeInput) -> ToolResult:
        status = self.manager.get_status()
        self.manager.merge(params.branch)
        return ToolResult.text(f"Merged {params.branch} into {status['branch']}")


class GitDeleteBranchInput(BaseModel):
    """Input for GitDeleteBranchTool."""

    branch: str = Field(..., description="Branch name to delete")
    force: bool = Field(default=False, description="Force delete unmerged branch")


class GitDeleteBranchTool(BaseTool):
    """Tool to delete a branch."""

    name = "git_delete_branch"
    description = "Delete a git branch (cannot delete protected branches)"
    args_model = GitDeleteBranchInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitDeleteBranchInput) -> ToolResult:
        self.manager.delete_branch(params.branch, force=params.force)
        return ToolResult.text(f"Deleted branch: {params.branch}")


class GitStashInput(BaseModel):
    """Input for GitStashTool."""

    action: str = Field(
        ...,
        description="Stash action: push (save), pop (restore), list",
        pattern="^(push|pop|list)$",
    )
    message: str | None = Field(
        default=None, description="Optional name for the stash (only for push)"
    )
    include_untracked: bool = Field(
        default=False, description="Include untracked files when stashing (git stash push -u)"
    )


class GitStashTool(BaseTool):
    """Tool to stash changes in a dirty working directory."""

    name = "git_stash"
    description = "Stash the changes in a dirty working directory (git stash)"
    args_model = GitStashInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitStashInput) -> ToolResult:
        if params.action == "push":
            self.manager.stash(message=params.message, include_untracked=params.include_untracked)
            if params.message:
                return ToolResult.text(f"Stashed changes: {params.message}")
            return ToolResult.text("Stashed current changes")
        if params.action == "pop":
            self.manager.stash_pop()
            return ToolResult.text("Applied and removed latest stash")
        if params.action == "list":
            stashes = self.manager.stash_list()
            if not stashes:
                return ToolResult.text("No stashes found")
            return ToolResult.text("\n".join(stashes))
        return ToolResult.text(f"Unknown action: {params.action}")


class GetParentBranchInput(BaseModel):
    """Input for GetParentBranchTool."""

    branch: str | None = Field(
        default=None, description="Branch name to inspect (default: current branch)"
    )


class GetParentBranchTool(BaseTool):
    """Tool to show a branch's configured parent branch.

    Issue #79: Parent branch is tracked in PhaseStateEngine state.
    """

    name = "get_parent_branch"
    description = "Detect parent branch for a branch (via PhaseStateEngine state)"
    args_model = GetParentBranchInput

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GetParentBranchInput) -> ToolResult:
        try:
            git = GitManager()
            branch = params.branch or git.get_current_branch()

            pm = project_manager.ProjectManager(workspace_root=self.workspace_root)
            engine = phase_state_engine.PhaseStateEngine(
                workspace_root=self.workspace_root,
                project_manager=pm,
            )
            state = await anyio.to_thread.run_sync(engine.get_state, branch)
            parent = state.get("parent_branch")

            if parent:
                return ToolResult.text(f"Branch: {branch}\nParent branch: {parent}")
            return ToolResult.text(f"Branch: {branch}\nParent branch: (not set)")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            return ToolResult.error(f"Failed to get parent branch: {exc}")
