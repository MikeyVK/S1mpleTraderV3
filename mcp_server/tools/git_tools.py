"""Git tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.core.logging import get_logger
from mcp_server.managers.git_manager import GitManager
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
            return ToolResult.text(f"✅ Created and switched to branch: {branch_name}")
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
        # 1. Switch branch
        self.manager.checkout(params.branch)

        # 2. Try to sync PhaseStateEngine state
        # pylint: disable=import-outside-toplevel
        import asyncio
        from pathlib import Path
        from mcp_server.managers.phase_state_engine import PhaseStateEngine
        from mcp_server.managers.project_manager import ProjectManager

        try:
            workspace_root = Path.cwd()
            project_manager = ProjectManager(workspace_root=workspace_root)
            engine = PhaseStateEngine(
                workspace_root=workspace_root,
                project_manager=project_manager
            )
            # Get state - this triggers auto-recovery and saves if needed
            state = engine.get_state(params.branch)
            
            # Give file I/O time to complete before returning
            await asyncio.sleep(0.1)
            
            current_phase = state.get('current_phase', 'unknown')
            parent_branch = state.get('parent_branch')

            # 3. Return enriched result with phase info
            output = (
                f"Switched to branch: {params.branch}\n"
                f"Current phase: {current_phase}"
            )
            if parent_branch:
                output += f"\nParent branch: {parent_branch}"

            return ToolResult.text(output)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # If state sync fails, still report successful branch switch
            logger.warning(
                "Branch switched but state sync failed",
                extra={"props": {"branch": params.branch, "error": str(e)}}
            )
            return ToolResult.text(
                f"Switched to branch: {params.branch}\n"
                f"(State sync unavailable: {str(e)})"
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
        return ToolResult.error(f"Unknown stash action: {params.action}")

class GetParentBranchInput(BaseModel):
    """Input for GetParentBranchTool."""
    branch: str | None = Field(
        default=None,
        description="Branch name to query (defaults to current branch)"
    )


class GetParentBranchTool(BaseTool):
    """Tool to get the parent branch for a given branch.

    Issue #79: Query parent_branch from PhaseStateEngine state to
    determine merge target for PRs.
    """

    name = "get_parent_branch"
    description = "Get the parent branch for a specified branch"
    args_model = GetParentBranchInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GetParentBranchInput) -> ToolResult:
        # 1. Determine which branch to query
        # pylint: disable=import-outside-toplevel
        from pathlib import Path
        from mcp_server.managers.phase_state_engine import PhaseStateEngine
        from mcp_server.managers.project_manager import ProjectManager

        try:
            workspace_root = Path.cwd()

            # Get branch name (current if not specified)
            branch_name = params.branch
            if not branch_name:
                branch_name = self.manager.get_current_branch()

            # 2. Query PhaseStateEngine state
            project_manager = ProjectManager(workspace_root=workspace_root)
            engine = PhaseStateEngine(
                workspace_root=workspace_root,
                project_manager=project_manager
            )
            state = engine.get_state(branch_name)
            parent_branch = state.get('parent_branch')

            # 3. Return result
            if parent_branch:
                return ToolResult.text(
                    f"Branch: {branch_name}\n"
                    f"Parent branch: {parent_branch}"
                )
            return ToolResult.text(
                f"Branch: {branch_name}\n"
                f"Parent branch: (not set)"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                "Failed to get parent branch",
                extra={"props": {"branch": params.branch, "error": str(e)}}
            )
            return ToolResult.error(f"Failed to get parent branch: {str(e)}")
