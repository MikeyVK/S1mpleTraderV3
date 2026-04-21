"""GitHub PR tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field, model_validator

from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IPRStatusWriter, PRStatus
from mcp_server.core.operation_notes import ExclusionNote, NoteContext, RecoveryNote
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.schemas import GitConfig
from mcp_server.tools.base import BaseTool, BranchMutatingTool
from mcp_server.tools.tool_result import ToolResult

if TYPE_CHECKING:
    from mcp_server.managers.git_manager import GitManager


class CreatePRInput(BaseModel):
    """Input for CreatePRTool."""

    _git_config: ClassVar[GitConfig | None] = None

    @classmethod
    def configure(cls, git_config: GitConfig) -> None:
        cls._git_config = git_config

    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    head: str = Field(..., description="Source branch")
    base: str | None = Field(default=None, description="Target branch")
    draft: bool = Field(default=False, description="Create as draft")

    @model_validator(mode="after")
    def apply_default_base_branch(self) -> CreatePRInput:
        if self.base is not None:
            return self

        git_config = self.__class__._git_config
        if git_config is None:
            raise ValueError("GitConfig must be injected before PR input validation")

        self.base = git_config.default_base_branch
        return self


class CreatePRTool(BaseTool):
    """Tool to create a GitHub Pull Request."""

    name = "create_pr"
    description = "Create a new GitHub Pull Request"
    args_model = CreatePRInput
    enforcement_event: str | None = "create_pr"

    def __init__(self, manager: GitHubManager, git_config: GitConfig) -> None:
        self.manager = manager
        self._git_config = git_config
        CreatePRInput.configure(git_config)

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: CreatePRInput, context: NoteContext) -> ToolResult:
        del context  # Not used
        result = self.manager.create_pr(
            title=params.title,
            body=params.body,
            head=params.head,
            base=params.base or self._git_config.default_base_branch,
            draft=params.draft,
        )

        return ToolResult.text(f"Created PR #{result['number']}: {result['url']}")


class ListPRsInput(BaseModel):
    """Input for ListPRsTool."""

    state: str = Field(
        default="open", description="Filter by PR state", pattern="^(open|closed|all)$"
    )
    base: str | None = Field(default=None, description="Filter by base branch")
    head: str | None = Field(default=None, description="Filter by head branch")


class ListPRsTool(BaseTool):
    """Tool to list pull requests."""

    name = "list_prs"
    description = "List pull requests with optional state/base/head filters"
    args_model = ListPRsInput

    def __init__(self, manager: GitHubManager, git_config: GitConfig) -> None:
        self.manager = manager
        self._git_config = git_config
        CreatePRInput.configure(git_config)

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: ListPRsInput, context: NoteContext) -> ToolResult:
        del context  # Not used
        try:
            prs = self.manager.list_prs(state=params.state, base=params.base, head=params.head)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        if not prs:
            return ToolResult.text("No pull requests found matching the criteria.")

        lines = [f"Found {len(prs)} pull request(s):\n"]
        for pr in prs:
            lines.append(
                f"- #{pr.number}: {pr.title}\n"
                f"  State: {pr.state} | Base: {pr.base.ref} | Head: {pr.head.ref}\n"
            )

        return ToolResult.text("\n".join(lines))


class MergePRInput(BaseModel):
    """Input for MergePRTool."""

    pr_number: int = Field(..., description="Pull request number to merge")
    commit_message: str | None = Field(
        default=None, description="Optional commit message for the merge"
    )
    merge_method: str = Field(
        default="merge", description="Merge strategy (only 'merge' is supported)", pattern="^merge$"
    )


class MergePRTool(BaseTool):
    """Tool to merge a pull request."""

    name = "merge_pr"
    description = "Merge a pull request with optional commit message and method"
    args_model = MergePRInput

    def __init__(self, manager: GitHubManager, git_config: GitConfig) -> None:
        self.manager = manager
        self._git_config = git_config
        CreatePRInput.configure(git_config)

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: MergePRInput, context: NoteContext) -> ToolResult:
        del context  # Not used
        try:
            result = self.manager.merge_pr(
                pr_number=params.pr_number,
                commit_message=params.commit_message,
                merge_method=params.merge_method,
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(
            f"Merged PR #{params.pr_number} using {params.merge_method} (SHA {result['sha']})"
        )


class SubmitPRInput(BaseModel):
    """Input for SubmitPRTool — atomic branch submission."""

    head: str = Field(..., description="Source branch name (e.g. feature/42-name)")
    title: str = Field(..., description="PR title")
    base: str | None = Field(default=None, description="Target branch (defaults to main)")
    body: str | None = Field(default=None, description="PR description (markdown)")
    draft: bool = Field(default=False, description="Create as draft PR")


class SubmitPRTool(BranchMutatingTool):
    """Atomic branch-submission tool.

    Performs: neutralize branch-local artifacts → commit → push → create PR
    → write PRStatus.OPEN to PRStatusCache in one tool call.

    Readiness gate (phase == ready) is enforced via enforcement.yaml, not here.
    Blocked when PRStatus.OPEN already exists on this branch (check_pr_status rule).
    """

    name = "submit_pr"
    description = "Atomically neutralize, commit, push, and create a PR for the current branch"
    args_model = SubmitPRInput
    enforcement_event: str | None = "submit_pr"

    def __init__(
        self,
        git_manager: GitManager,
        github_manager: GitHubManager,
        pr_status_writer: IPRStatusWriter,
    ) -> None:
        self._git_manager = git_manager
        self._github_manager = github_manager
        self._pr_status_writer = pr_status_writer

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: SubmitPRInput, context: NoteContext) -> ToolResult:
        """Atomic: neutralize → commit → push → create_pr → set_pr_status(OPEN)."""
        branch = self._git_manager.adapter.get_current_branch()
        base = params.base or self._git_manager.git_config.default_base_branch

        # Step 1-3: neutralize branch-local artifacts if ExclusionNotes present
        excluded_paths = frozenset(n.file_path for n in context.of_type(ExclusionNote))
        if excluded_paths:
            self._git_manager.adapter.neutralize_to_base(excluded_paths, base)

        # Step 4-7: commit → push → create_pr → write OPEN status
        try:
            self._git_manager.commit_with_scope(
                workflow_phase="ready",
                message=f"neutralize branch-local artifacts to '{base}'",
                note_context=context,
                commit_type="chore",
            )
            self._git_manager.adapter.push()
            result = self._github_manager.create_pr(
                title=params.title,
                body=params.body or "",
                head=params.head,
                base=base,
                draft=params.draft,
            )
        except ExecutionError as exc:
            context.produce(
                RecoveryNote(
                    message=f"submit_pr failed after neutralize: {exc}. "
                    "Branch tip may have been modified. Run git status to inspect."
                )
            )
            return ToolResult.error(str(exc))

        self._pr_status_writer.set_pr_status(branch, PRStatus.OPEN)
        return ToolResult.text(f"Created PR #{result['number']}: {result['url']}")
