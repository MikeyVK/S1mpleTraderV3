"""Git tools."""
from typing import Any

from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool, ToolResult


class CreateBranchTool(BaseTool):
    """Tool to create a git branch."""

    name = "create_feature_branch"
    description = "Create a new feature branch"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Branch name (kebab-case)"},
                "branch_type": {
                    "type": "string",
                    "enum": ["feature", "fix", "refactor", "docs"],
                    "default": "feature"
                }
            },
            "required": ["name"]
        }

    async def execute(
        self, name: str, branch_type: str = "feature", **kwargs: Any
    ) -> ToolResult:
        branch_name = self.manager.create_feature_branch(name, branch_type)
        return ToolResult.text(f"Created and switched to branch: {branch_name}")

class GitStatusTool(BaseTool):
    """Tool to check git status."""

    name = "git_status"
    description = "Check current git status"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    async def execute(self, **kwargs: Any) -> ToolResult:
        status = self.manager.get_status()

        text = f"Branch: {status['branch']}\n"
        text += f"Clean: {status['is_clean']}\n"
        if status['untracked_files']:
            text += f"Untracked: {', '.join(status['untracked_files'])}\n"
        if status['modified_files']:
            text += f"Modified: {', '.join(status['modified_files'])}\n"

        return ToolResult.text(text)


class GitCommitTool(BaseTool):
    """Tool to commit changes with TDD phase prefix."""

    name = "git_add_or_commit"
    description = "Commit changes with TDD phase prefix (red/green/refactor/docs)"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["red", "green", "refactor", "docs"],
                    "description": "TDD phase (red=test, green=feat, refactor, docs)"
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (without prefix)"
                }
            },
            "required": ["phase", "message"]
        }

    async def execute(
        self, phase: str, message: str, **kwargs: Any
    ) -> ToolResult:
        if phase == "docs":
            commit_hash = self.manager.commit_docs(message)
        else:
            commit_hash = self.manager.commit_tdd_phase(phase, message)
        return ToolResult.text(f"Committed: {commit_hash}")


class GitCheckoutTool(BaseTool):
    """Tool to checkout to a branch."""

    name = "git_checkout"
    description = "Switch to an existing branch"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "Branch name to checkout"
                }
            },
            "required": ["branch"]
        }

    async def execute(self, branch: str, **kwargs: Any) -> ToolResult:
        self.manager.checkout(branch)
        return ToolResult.text(f"Switched to branch: {branch}")


class GitPushTool(BaseTool):
    """Tool to push current branch to origin."""

    name = "git_push"
    description = "Push current branch to origin remote"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "set_upstream": {
                    "type": "boolean",
                    "description": "Set upstream tracking (for new branches)",
                    "default": False
                }
            },
            "required": []
        }

    async def execute(self, set_upstream: bool = False, **kwargs: Any) -> ToolResult:
        status = self.manager.get_status()
        self.manager.push(set_upstream=set_upstream)
        return ToolResult.text(f"Pushed branch: {status['branch']}")


class GitMergeTool(BaseTool):
    """Tool to merge a branch into current branch."""

    name = "git_merge"
    description = "Merge a branch into the current branch"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "Branch name to merge"
                }
            },
            "required": ["branch"]
        }

    async def execute(self, branch: str, **kwargs: Any) -> ToolResult:
        status = self.manager.get_status()
        self.manager.merge(branch)
        return ToolResult.text(
            f"Merged {branch} into {status['branch']}"
        )


class GitDeleteBranchTool(BaseTool):
    """Tool to delete a branch."""

    name = "git_delete_branch"
    description = "Delete a git branch (cannot delete protected branches)"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "branch": {
                    "type": "string",
                    "description": "Branch name to delete"
                },
                "force": {
                    "type": "boolean",
                    "description": "Force delete unmerged branch",
                    "default": False
                }
            },
            "required": ["branch"]
        }

    async def execute(
        self, branch: str, force: bool = False, **kwargs: Any
    ) -> ToolResult:
        self.manager.delete_branch(branch, force=force)
        return ToolResult.text(f"Deleted branch: {branch}")


class GitStashTool(BaseTool):
    """Tool to stash changes in a dirty working directory."""

    name = "git_stash"
    description = "Stash the changes in a dirty working directory (git stash)"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["push", "pop", "list"],
                    "description": "Stash action: push (save), pop (restore), list"
                },
                "message": {
                    "type": "string",
                    "description": "Optional name for the stash (only for push)"
                }
            },
            "required": ["action"]
        }

    async def execute(
        self, action: str, message: str | None = None, **kwargs: Any
    ) -> ToolResult:
        if action == "push":
            self.manager.stash(message=message)
            if message:
                return ToolResult.text(f"Stashed changes: {message}")
            return ToolResult.text("Stashed current changes")
        if action == "pop":
            self.manager.stash_pop()
            return ToolResult.text("Applied and removed latest stash")
        if action == "list":
            stashes = self.manager.stash_list()
            if not stashes:
                return ToolResult.text("No stashes found")
            return ToolResult.text("\n".join(stashes))
        return ToolResult.text(f"Unknown action: {action}")
