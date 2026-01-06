"""Git tools."""
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import anyio
from pydantic import BaseModel, Field

from mcp_server.core.exceptions import MCPError
from mcp_server.core.logging import get_logger
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.base import BaseTool, ToolResult

logger = get_logger("tools.git")


def _input_schema(args_model: type[BaseModel] | None) -> dict[str, Any]:
    if args_model is None:
        return {}
    return args_model.model_json_schema()


class CreateBranchInput(BaseModel):
    """Input for CreateBranchTool."""
    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(
        default="feature",
        description="Branch type",
        pattern="^(feature|fix|refactor|docs|epic)$"
    )
    base_branch: str = Field(
        ...,
        description="Base branch to create from (e.g., 'HEAD', 'main', 'refactor/51-labels-yaml')"
    )


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
            extra={"props": {
                "name": params.name,
                "branch_type": params.branch_type,
                "base_branch": params.base_branch
            }}
        )

        try:
            branch_name = self.manager.create_branch(
                params.name,
                params.branch_type,
                params.base_branch
            )
            return ToolResult.text(f"âœ… Created and switched to branch: {branch_name}")
        except Exception as e:
            logger.error(
                "Branch creation failed",
                extra={"props": {
                    "name": params.name,
                    "error": str(e)
                }}
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

    async def execute(self, params: GitStatusInput) -> ToolResult:
        status = self.manager.get_status()

        text = f"Branch: {status['branch']}\n"
        text += f"Clean: {status['is_clean']}\n"
        if status['untracked_files']:
            text += f"Untracked: {', '.join(status['untracked_files'])}\n"
        if status['modified_files']:
            text += f"Modified: {', '.join(status['modified_files'])}\n"

        return ToolResult.text(text)


class GitCommitInput(BaseModel):
    """Input for GitCommitTool."""
    phase: str = Field(
        ...,
        description="TDD phase (red=test, green=feat, refactor, docs)",
        pattern="^(red|green|refactor|docs)$"
    )
    message: str = Field(..., description="Commit message (without prefix)")
    files: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of file paths to stage and commit. When omitted, commits all changes."
        )
    )


class GitCommitTool(BaseTool):
    """Tool to commit changes with TDD phase prefix."""

    name = "git_add_or_commit"
    description = "Commit changes with TDD phase prefix (red/green/refactor/docs)"
    args_model = GitCommitInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitCommitInput) -> ToolResult:
        if params.phase == "docs":
            commit_hash = self.manager.commit_docs(params.message, files=params.files)
        else:
            commit_hash = self.manager.commit_tdd_phase(
                params.phase,
                params.message,
                files=params.files,
            )
        return ToolResult.text(f"Committed: {commit_hash}")


class GitRestoreInput(BaseModel):
    """Input for GitRestoreTool."""

    files: list[str] = Field(
        ...,
        min_length=1,
        description="File paths to restore (discard local changes)"
    )
    source: str = Field(
        default="HEAD",
        description="Git ref to restore from (default: HEAD)"
    )


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
        return ToolResult.text(
            f"Restored {len(params.files)} file(s) from {params.source}"
        )


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
            return ToolResult.error(f"Checkout failed for branch: {params.branch}")

        current_phase = "unknown"
        try:
            project_manager = ProjectManager(workspace_root=workspace_root)
            engine = PhaseStateEngine(
                workspace_root=workspace_root,
                project_manager=project_manager,
            )
            state = await anyio.to_thread.run_sync(engine.get_state, params.branch)
            current_phase = state.get("current_phase") or "unknown"
        except (MCPError, ValueError, OSError) as exc:
            logger.warning(
                "Phase state sync failed after checkout",
                extra={"props": {"branch": params.branch, "error": str(exc)}},
            )

        return ToolResult.text(
            f"Switched to branch: {params.branch}\n"
            f"Phase: {current_phase}"
        )


class GitPushInput(BaseModel):
    """Input for GitPushTool."""
    set_upstream: bool = Field(
        default=False,
        description="Set upstream tracking (for new branches)"
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
        return ToolResult.text(
            f"Merged {params.branch} into {status['branch']}"
        )


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
        pattern="^(push|pop|list)$"
    )
    message: str | None = Field(
        default=None,
        description="Optional name for the stash (only for push)"
    )
    include_untracked: bool = Field(
        default=False,
        description="Include untracked files when stashing (git stash push -u)"
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
        default=None,
        description="Branch name to inspect (default: current branch)"
    )


class GetParentBranchTool(BaseTool):
    """Tool to detect a branch's parent branch.

    Uses git reflog and searches for: "checkout: moving from <parent> to <branch>".

    Notes:
    - Runs git with --no-pager and stdin closed to avoid stdio hangs.
    """

    name = "get_parent_branch"
    description = "Detect parent branch for a branch (via git reflog)"
    args_model = GetParentBranchInput

    def __init__(
        self,
        workspace_root: Path | None = None,
        manager: GitManager | None = None,
    ) -> None:
        self.workspace_root = workspace_root or Path.cwd()
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    def _detect_parent_branch_from_reflog(self, branch: str) -> str | None:
        env = os.environ.copy()
        env.setdefault("GIT_PAGER", "cat")
        env.setdefault("PAGER", "cat")
        env.setdefault("GIT_TERMINAL_PROMPT", "0")

        result = subprocess.run(
            ["git", "--no-pager", "reflog", "show", "--all"],
            cwd=self.workspace_root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
            env=env,
        )

        pattern = re.compile(
            r"checkout: moving from (.+?) to " + re.escape(branch)
        )
        for line in result.stdout.splitlines():
            match = pattern.search(line)
            if match:
                return match.group(1)
        return None

    async def execute(self, params: GetParentBranchInput) -> ToolResult:
        try:
            branch = params.branch or self.manager.get_current_branch()
            parent = await anyio.to_thread.run_sync(
                self._detect_parent_branch_from_reflog,
                branch,
            )

            if parent:
                return ToolResult.text(
                    f"Branch: {branch}\nParent branch: {parent}"
                )
            return ToolResult.text(
                f"Branch: {branch}\nParent branch: (not detected)"
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            return ToolResult.error(f"Failed to detect parent branch: {exc}")
