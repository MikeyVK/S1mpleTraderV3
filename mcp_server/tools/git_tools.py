"""Git tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool, ToolResult


class CreateBranchInput(BaseModel):
    """Input for CreateBranchTool."""
    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(
        default="feature",
        description="Branch type",
        pattern="^(feature|fix|refactor|docs)$"
    )


class CreateBranchTool(BaseTool):
    """Tool to create a git branch."""

    name = "create_feature_branch"
    description = "Create a new feature branch"
    args_model = CreateBranchInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: CreateBranchInput) -> ToolResult:
        branch_name = self.manager.create_feature_branch(params.name, params.branch_type)
        return ToolResult.text(f"Created and switched to branch: {branch_name}")


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
        return self.args_model.model_json_schema()

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


class GitCommitTool(BaseTool):
    """Tool to commit changes with TDD phase prefix."""

    name = "git_add_or_commit"
    description = "Commit changes with TDD phase prefix (red/green/refactor/docs)"
    args_model = GitCommitInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: GitCommitInput) -> ToolResult:
        if params.phase == "docs":
            commit_hash = self.manager.commit_docs(params.message)
        else:
            commit_hash = self.manager.commit_tdd_phase(params.phase, params.message)
        return ToolResult.text(f"Committed: {commit_hash}")


class GitCheckoutInput(BaseModel):
    """Input for GitCheckoutTool."""
    branch: str = Field(..., description="Branch name to checkout")


class GitCheckoutTool(BaseTool):
    """Tool to checkout to a branch."""

    name = "git_checkout"
    description = "Switch to an existing branch"
    args_model = GitCheckoutInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: GitCheckoutInput) -> ToolResult:
        self.manager.checkout(params.branch)
        return ToolResult.text(f"Switched to branch: {params.branch}")


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
        return self.args_model.model_json_schema()

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
        return self.args_model.model_json_schema()

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
        return self.args_model.model_json_schema()

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


class GitStashTool(BaseTool):
    """Tool to stash changes in a dirty working directory."""

    name = "git_stash"
    description = "Stash the changes in a dirty working directory (git stash)"
    args_model = GitStashInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: GitStashInput) -> ToolResult:
        if params.action == "push":
            self.manager.stash(message=params.message)
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
