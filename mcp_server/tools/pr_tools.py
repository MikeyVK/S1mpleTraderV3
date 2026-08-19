"""GitHub PR tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.exceptions import ExecutionError, PreflightError
from mcp_server.core.interfaces import IBranchParentReader, ICoreTool, IPRStatusWriter, PRStatus
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.schemas import GitConfig
from mcp_server.schemas.github_models import PRReadModel
from mcp_server.schemas.tool_outputs import ListPRsOutput, MergePROutput, PROutput, PRSummaryDTO

if TYPE_CHECKING:
    from mcp_server.managers.git_manager import GitManager


class ListPRsInput(BaseModel):
    """Input for ListPRsTool."""

    model_config = ConfigDict(extra="forbid")

    state: str = Field(
        default="open", description="Filter by PR state", pattern="^(open|closed|all)$"
    )
    base: str | None = Field(default=None, description="Filter by base branch")
    head: str | None = Field(default=None, description="Filter by head branch")


def _map_pr_to_output(pr: PRReadModel) -> PROutput:
    return PROutput(
        number=pr.pr_number,
        title=pr.title,
        html_url=pr.html_url,
        state=pr.state,
        base_ref=pr.base_branch,
        head_ref=pr.head_branch,
        merged_at=pr.merged_at,
        merge_sha=pr.merge_sha,
        body=pr.body,
    )


class ListPRsTool(ICoreTool[ListPRsInput, ListPRsOutput]):
    """Tool to list pull requests."""

    @property
    def name(self) -> str:
        return "list_prs"

    @property
    def description(self) -> str:
        return "List pull requests with optional state/base/head filters"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return ListPRsInput

    def __init__(self, manager: GitHubManager, git_config: GitConfig) -> None:
        self.manager = manager
        self._git_config = git_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: ListPRsInput, context: NoteContext) -> ListPRsOutput:
        del context  # Not used
        try:
            prs = self.manager.list_prs(state=params.state, base=params.base, head=params.head)
            pull_requests = [
                PRSummaryDTO(
                    number=pr.number,
                    title=pr.title,
                    state=pr.state,
                    html_url=pr.html_url,
                    base_ref=pr.base.ref,
                    head_ref=pr.head.ref,
                )
                for pr in prs
            ]
            return ListPRsOutput(
                prs_count=len(pull_requests),
                pull_requests=pull_requests,
            )
        except Exception as e:
            raise ExecutionError(str(e)) from e


class MergePRInput(BaseModel):
    """Input for MergePRTool."""

    model_config = ConfigDict(extra="forbid")

    pr_number: int = Field(..., description="Pull request number to merge")
    commit_message: str | None = Field(
        default=None, description="Optional commit message for the merge"
    )
    merge_method: str = Field(
        default="merge", description="Merge strategy (only 'merge' is supported)", pattern="^merge$"
    )


class MergePRTool(ICoreTool[MergePRInput, MergePROutput]):
    """Tool to merge a pull request."""

    @property
    def name(self) -> str:
        return "merge_pr"

    @property
    def description(self) -> str:
        return "Merge a pull request with optional commit message and method"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return MergePRInput

    def __init__(
        self,
        manager: GitHubManager,
        git_config: GitConfig,
        pr_status_writer: IPRStatusWriter,
    ) -> None:
        self.manager = manager
        self._git_config = git_config
        self._pr_status_writer = pr_status_writer

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: MergePRInput, context: NoteContext) -> MergePROutput:
        del context  # Not used
        try:
            model = self.manager.get_pr(params.pr_number)
            head_branch = model.head_branch
            result = self.manager.merge_pr(
                pr_number=params.pr_number,
                commit_message=params.commit_message,
                merge_method=params.merge_method,
            )
            self._pr_status_writer.set_pr_status(head_branch, PRStatus.ABSENT)
            return MergePROutput(
                pr_number=params.pr_number,
                merge_sha=result["sha"],
                merge_method=params.merge_method,
            )
        except Exception as e:
            raise ExecutionError(str(e)) from e


class GetPRInput(BaseModel):
    """Input for GetPRTool."""

    model_config = ConfigDict(extra="forbid")

    pr_number: int = Field(..., description="Pull request number")


class GetPRTool(ICoreTool[GetPRInput, PROutput]):
    """Tool to get a single pull request."""

    @property
    def name(self) -> str:
        return "get_pr"

    @property
    def description(self) -> str:
        return "Get detailed information about a specific pull request"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return GetPRInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: GetPRInput, context: NoteContext) -> PROutput:
        del context  # Not used
        try:
            pr = self.manager.get_pr(params.pr_number)
            return _map_pr_to_output(pr)
        except Exception as e:
            raise ExecutionError(str(e)) from e


class SubmitPRInput(BaseModel):
    """Input for SubmitPRTool — atomic branch submission."""

    model_config = ConfigDict(extra="forbid")

    head: str = Field(..., description="Source branch name (e.g. feature/42-name)")
    title: str = Field(..., description="PR title")
    base: str | None = Field(
        default=None,
        description=(
            "Target branch (defaults to main). "
            "Cascade: explicit value -> state.json parent_branch -> git_config.default_base_branch."
        ),
    )
    body: str | None = Field(default=None, description="PR description (markdown)")
    draft: bool = Field(default=False, description="Create as draft PR")


class SubmitPRTool(ICoreTool[SubmitPRInput, PROutput]):
    """Atomic branch-submission tool.

    Performs: neutralize branch-local artifacts -> commit -> push -> create PR
    -> write PRStatus.OPEN to PRStatusCache in one tool call.

    Readiness gate (phase == ready) is enforced via enforcement.yaml, not here.
    Blocked when PRStatus.OPEN already exists on this branch (check_pr_status rule).
    """

    enforcement_event: str | None = "submit_pr"

    @property
    def name(self) -> str:
        return "submit_pr"

    @property
    def description(self) -> str:
        return "Atomically neutralize, commit, push, and create a PR for the current branch"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return SubmitPRInput

    def __init__(
        self,
        git_manager: GitManager,
        github_manager: GitHubManager,
        pr_status_writer: IPRStatusWriter,
        merge_readiness_context: MergeReadinessContext,
        branch_parent_reader: IBranchParentReader,
    ) -> None:
        self._git_manager = git_manager
        self._github_manager = github_manager
        self._pr_status_writer = pr_status_writer
        self._merge_readiness_context = merge_readiness_context
        self._branch_parent_reader = branch_parent_reader

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: SubmitPRInput, context: NoteContext) -> PROutput:
        branch = self._git_manager.get_current_branch()
        base = (
            params.base
            or self._branch_parent_reader.get_parent_branch(branch)
            or self._git_manager.git_config.default_base_branch
        )
        artifact_paths = frozenset(
            a.path for a in self._merge_readiness_context.branch_local_artifacts
        )
        # [GIT] Full git transaction
        try:
            commit_made = self._git_manager.prepare_submission(artifact_paths, base, context)
        except (PreflightError, ExecutionError) as exc:
            raise ExecutionError(str(exc)) from exc
        # [GITHUB] Create PR — rollback push on failure
        try:
            result = self._github_manager.create_pr(
                title=params.title,
                body=params.body or "",
                head=params.head,
                base=base,
                draft=params.draft,
            )
        except ExecutionError as exc:
            if commit_made:
                try:
                    self._git_manager.rollback_push(context)
                    context.produce(
                        Note(
                            key="submit_pr_api_failed_with_rollback_recovery",
                            params={"error_details": str(exc)},
                        )
                    )
                except ExecutionError:
                    pass  # RecoveryNote already produced by rollback_push
            raise ExecutionError(str(exc)) from exc
        # [STATUS] Record PR as open
        self._pr_status_writer.set_pr_status(branch, PRStatus.OPEN)

        try:
            pr_read = self._github_manager.get_pr(result["number"])
            return _map_pr_to_output(pr_read)
        except Exception as e:
            raise ExecutionError(f"PR created but retrieval/mapping failed: {e}") from e
