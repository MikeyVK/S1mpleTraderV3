"""Issue management tools."""

import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.config.schemas.contracts_config import ContractsConfig
from mcp_server.config.schemas.git_config import GitConfig
from mcp_server.config.schemas.label_config import LabelConfig
from mcp_server.config.schemas.scope_config import ScopeConfig
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.schemas import (
    IssueConfig,
    MilestoneConfig,
)
from mcp_server.schemas.github_models import IssueReadModel
from mcp_server.schemas.tool_outputs import (
    CloseIssueOutput,
    IssueOutput,
    IssueSummaryDTO,
    ListIssuesOutput,
)

IssueState = Literal["open", "closed", "all"]


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text for safe JSON-RPC transmission.

    Preserves emoji and other Unicode while fixing malformed surrogates.
    """
    try:
        utf8_bytes = text.encode("utf-8", errors="surrogatepass")
    except UnicodeEncodeError:
        utf8_bytes = text.encode("utf-8", errors="replace")

    normalized = utf8_bytes.decode("utf-8", errors="replace")
    return unicodedata.normalize("NFC", normalized)


class CreateIssueInput(BaseModel):
    """Structured input for creating a GitHub issue.

    Only structural validation happens here. Semantic validation against project
    config is delegated to GitHubManager.validate_issue_params(). No free-form
    labels are accepted; they are assembled internally by CreateIssueTool.

    The body field accepts pre-rendered markdown. Use scaffold_artifact(artifact_type='issue')
    to generate the body before calling this tool.
    """

    issue_type: str = Field(..., description="Issue type: feature, bug, hotfix, chore, docs, epic")
    title: str = Field(..., description="Issue title")
    priority: str = Field(..., description="Priority value")
    scope: str = Field(
        ...,
        description=(
            "Scope from scopes.yaml: architecture, mcp-server, platform,"
            " tooling, workflow, documentation"
        ),
    )
    body: str = Field(
        ...,
        description=(
            "Issue body as pre-rendered markdown. "
            "Use scaffold_artifact(artifact_type='issue') to generate."
        ),
    )
    is_epic: bool = Field(default=False, description="Mark this issue as an epic")
    parent_issue: int | None = Field(
        default=None, description="Parent issue number (positive integer)", ge=1
    )
    milestone: str | None = Field(default=None, description="Milestone title")
    assignees: list[str] | None = Field(default=None, description="List of GitHub logins to assign")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "issue_type": "feature",
                    "title": "Add structured issue creation",
                    "priority": "medium",
                    "scope": "mcp-server",
                    "body": "## Problem\n\nThe create_issue tool lacks validation.",
                },
                {
                    "issue_type": "bug",
                    "title": "Login fails on Windows when username contains spaces",
                    "priority": "high",
                    "scope": "platform",
                    "body": (
                        "## Problem\n\nLogin fails with 500 error."
                        "\n\n## Expected Behavior\n\nRedirect to dashboard."
                    ),
                    "is_epic": False,
                    "parent_issue": 91,
                    "milestone": "v2.0",
                    "assignees": ["alice"],
                },
            ]
        },
    )


def _map_issue_to_output(issue: IssueReadModel) -> IssueOutput:
    milestone_title = issue.milestone.title if issue.milestone else "None"
    assignees_summary = ", ".join(issue.assignees) if issue.assignees else "Unassigned"
    return IssueOutput(
        number=issue.number,
        title=issue.title,
        state=issue.state,
        milestone_title=milestone_title,
        assignees_summary=assignees_summary,
        html_url=issue.url,
        body=issue.body,
        labels=issue.labels,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        closed_at=issue.closed_at,
        author=issue.author,
    )


class CreateIssueTool(ICoreTool[CreateIssueInput, IssueOutput]):
    """Tool to create a new GitHub issue."""

    @property
    def name(self) -> str:
        return "create_issue"

    @property
    def description(self) -> str:
        return "Create a new GitHub issue"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return CreateIssueInput

    def __init__(
        self,
        manager: GitHubManager,
        issue_config: IssueConfig,
        milestone_config: MilestoneConfig,
        contracts_config: ContractsConfig,
        label_config: LabelConfig | None = None,
        scope_config: ScopeConfig | None = None,
        git_config: GitConfig | None = None,
    ) -> None:
        self.manager = manager
        self._issue_config = issue_config
        self._milestone_config = milestone_config
        self._contracts_config = contracts_config
        self._label_config = label_config
        self._scope_config = scope_config
        self._git_config = git_config

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        schema = self.args_model.model_json_schema()
        schema["properties"]["issue_type"]["enum"] = [
            e.name for e in self._issue_config.issue_types
        ]
        if self._label_config is not None:
            priority_labels = self._label_config.get_labels_by_category("priority")
            schema["properties"]["priority"]["enum"] = [
                lbl.name.split(":")[-1] for lbl in priority_labels
            ]
        if self._scope_config is not None:
            schema["properties"]["scope"]["enum"] = self._scope_config.scopes
        if self._git_config is not None:
            schema["properties"]["title"]["maxLength"] = self._git_config.issue_title_max_length
        return schema

    def _assemble_labels(self, params: CreateIssueInput) -> list[str]:
        """Assemble the full label list from structured input fields."""
        issue_cfg = self._issue_config
        workflow_cfg = self._contracts_config

        type_label = "type:epic" if params.is_epic else issue_cfg.get_label(params.issue_type)
        workflow_name = issue_cfg.get_workflow(params.issue_type)
        first_phase = workflow_cfg.get_first_phase(workflow_name)
        phase_label = f"phase:{first_phase}"

        labels: list[str] = [
            type_label,
            f"scope:{params.scope}",
            f"priority:{params.priority}",
            phase_label,
        ]

        if params.parent_issue is not None:
            labels.append(f"parent:{params.parent_issue}")

        return labels

    async def execute(self, params: CreateIssueInput, context: NoteContext) -> IssueOutput:
        del context  # Not used
        try:
            self.manager.validate_issue_params(
                issue_type=params.issue_type,
                title=params.title,
                priority=params.priority,
                scope=params.scope,
                milestone=params.milestone,
                assignees=params.assignees,
            )
        except ValueError as e:
            raise ExecutionError(f"Issue validation failed: {e}.") from e

        try:
            title_safe = normalize_unicode(params.title)
            body_safe = normalize_unicode(params.body)
            labels = self._assemble_labels(params)

            milestone_number: int | None = None
            if params.milestone is not None:
                milestone_number = next(
                    (
                        milestone.number
                        for milestone in self._milestone_config.milestones
                        if milestone.title == params.milestone
                    ),
                    None,
                )

            issue = self.manager.create_issue(
                title=title_safe,
                body=body_safe,
                labels=labels,
                milestone=milestone_number,
                assignees=params.assignees,
            )
            issue_read = self.manager.get_issue(issue["number"])
            return _map_issue_to_output(issue_read)
        except ValueError as e:
            raise ExecutionError(f"Label assembly failed: {e}.") from e
        except Exception as e:
            raise ExecutionError(str(e)) from e


class GetIssueInput(BaseModel):
    """Input for GetIssueTool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="The issue number to retrieve")


class GetIssueTool(ICoreTool[GetIssueInput, IssueOutput]):
    """Tool to get issue details."""

    @property
    def name(self) -> str:
        return "get_issue"

    @property
    def description(self) -> str:
        return "Get detailed information about a specific GitHub issue"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return GetIssueInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: GetIssueInput, context: NoteContext) -> IssueOutput:
        del context  # Not used
        try:
            issue = self.manager.get_issue(params.issue_number)
            return _map_issue_to_output(issue)
        except Exception as e:
            raise ExecutionError(str(e)) from e


class ListIssuesInput(BaseModel):
    """Input for ListIssuesTool."""

    model_config = ConfigDict(extra="forbid")

    state: IssueState | None = Field(default=None, description="Filter by issue state")
    labels: list[str] | None = Field(default=None, description="Filter by labels")


class ListIssuesTool(ICoreTool[ListIssuesInput, ListIssuesOutput]):
    """Tool to list issues."""

    @property
    def name(self) -> str:
        return "list_issues"

    @property
    def description(self) -> str:
        return "List GitHub issues with optional filtering by state and labels"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return ListIssuesInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: ListIssuesInput, context: NoteContext) -> ListIssuesOutput:
        del context  # Not used
        try:
            state_str = params.state
            issues = self.manager.list_issues(state=state_str or "open", labels=params.labels)

            issues_list = []
            for issue in issues:
                assignees_summary = (
                    ", ".join(u.login for u in issue.assignees)
                    if getattr(issue, "assignees", None)
                    else "Unassigned"
                )
                created_at_str = (
                    issue.created_at.isoformat()
                    if hasattr(issue.created_at, "isoformat")
                    else str(issue.created_at)
                )

                issues_list.append(
                    IssueSummaryDTO(
                        number=issue.number,
                        title=issue.title,
                        state=issue.state,
                        html_url=issue.html_url,
                        labels=[lbl.name for lbl in issue.labels]
                        if hasattr(issue, "labels")
                        else [],
                        assignees_summary=assignees_summary,
                        created_at=created_at_str,
                    )
                )
            return ListIssuesOutput(
                issues_count=len(issues_list),
                issues=issues_list,
            )
        except Exception as e:
            raise ExecutionError(str(e)) from e


class UpdateIssueInput(BaseModel):
    """Input for UpdateIssueTool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="Issue number to update")
    title: str | None = Field(default=None, description="New title")
    body: str | None = Field(default=None, description="Updated description")
    state: IssueState | None = Field(default=None, description="Target state")
    labels: list[str] | None = Field(default=None, description="Replace labels with this list")
    milestone: int | None = Field(default=None, description="Milestone number to assign")
    assignees: list[str] | None = Field(
        default=None, description="Replace assignees with this list"
    )


class UpdateIssueTool(ICoreTool[UpdateIssueInput, IssueOutput]):
    """Tool to update an issue."""

    @property
    def name(self) -> str:
        return "update_issue"

    @property
    def description(self) -> str:
        return "Update title, body, state, labels, milestone, or assignees for an issue"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return UpdateIssueInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: UpdateIssueInput, context: NoteContext) -> IssueOutput:
        del context  # Not used
        try:
            updated = self.manager.update_issue(
                issue_number=params.issue_number,
                title=params.title,
                body=params.body,
                state=params.state,
                labels=params.labels,
                assignees=params.assignees,
                milestone=params.milestone,
            )
            issue_read = self.manager.get_issue(updated.number)
            return _map_issue_to_output(issue_read)
        except Exception as e:
            raise ExecutionError(str(e)) from e


class CloseIssueInput(BaseModel):
    """Input for CloseIssueTool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="Issue number to close")
    comment: str | None = Field(default=None, description="Optional closing comment")


class CloseIssueTool(ICoreTool[CloseIssueInput, CloseIssueOutput]):
    """Tool to close an issue."""

    @property
    def name(self) -> str:
        return "close_issue"

    @property
    def description(self) -> str:
        return "Close a GitHub issue with an optional comment"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return CloseIssueInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: CloseIssueInput, context: NoteContext) -> CloseIssueOutput:
        del context  # Not used
        try:
            self.manager.close_issue(params.issue_number, comment=params.comment)
            return CloseIssueOutput(issue_number=params.issue_number)
        except Exception as e:
            raise ExecutionError(str(e)) from e
