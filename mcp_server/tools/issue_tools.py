"""Issue management tools."""

import copy
import json
import unicodedata
from typing import Any, Literal, cast

import jinja2
from pydantic import BaseModel, Field, field_validator

from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.template_introspector import introspect_template_with_inheritance
from mcp_server.scaffolding.version_hash import compute_version_hash
from mcp_server.schemas import (
    IssueConfig,
    MilestoneConfig,
    WorkflowConfig,
)
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.core.operation_notes import NoteContext
from mcp_server.utils.template_config import get_template_root

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


def _resolve_schema_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline all $ref references in a JSON Schema."""
    schema = copy.deepcopy(schema)
    defs: dict[str, Any] = schema.pop("$defs", {})

    def _resolve(node: Any) -> Any:  # noqa: ANN401
        if isinstance(node, dict):
            if "$ref" in node:
                ref_path: str = node["$ref"]
                def_name = ref_path.rsplit("/", maxsplit=1)[-1]
                resolved = copy.deepcopy(defs.get(def_name, {}))
                for key, value in node.items():
                    if key != "$ref":
                        resolved[key] = value
                return _resolve(resolved)
            return {key: _resolve(value) for key, value in node.items()}
        if isinstance(node, list):
            return [_resolve(item) for item in node]
        return node

    return cast(dict[str, Any], _resolve(schema))


class IssueBody(BaseModel):
    """Structured body for a GitHub issue, rendered via issue.md.jinja2."""

    problem: str = Field(..., description="Clear description of the problem or feature request")
    expected: str | None = Field(default=None, description="Expected behavior")
    actual: str | None = Field(default=None, description="Actual behavior observed")
    context: str | None = Field(default=None, description="Relevant background or environment info")
    steps_to_reproduce: str | None = Field(
        default=None, description="Numbered steps to reproduce the issue"
    )
    related_docs: list[str] | None = Field(
        default=None, description="List of related documentation paths or URLs"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "problem": "The create_issue tool does not validate issue_type.",
                },
                {
                    "problem": "Login fails on Windows when username contains spaces.",
                    "expected": "Login succeeds and redirects to dashboard.",
                    "actual": "500 Internal Server Error is returned.",
                    "context": "Observed on Windows 11, Python 3.13.",
                    "steps_to_reproduce": "1. Enter username with space\n2. Click Login",
                    "related_docs": ["docs/development/issue149/research.md"],
                },
            ]
        }
    }


class CreateIssueInput(BaseModel):
    """Structured input for creating a GitHub issue.

    Only structural validation happens here. Semantic validation against project
    config is delegated to GitHubManager.validate_issue_params(). No free-form
    labels are accepted; they are assembled internally by CreateIssueTool.
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
    body: IssueBody = Field(..., description="Structured issue body (IssueBody)")
    is_epic: bool = Field(default=False, description="Mark this issue as an epic")
    parent_issue: int | None = Field(
        default=None, description="Parent issue number (positive integer)", ge=1
    )
    milestone: str | None = Field(default=None, description="Milestone title")
    assignees: list[str] | None = Field(default=None, description="List of GitHub logins to assign")

    @field_validator("body", mode="before")
    @classmethod
    def coerce_body_from_json_string(cls, v: object) -> object:
        """Accept a JSON string for body and parse it into a dict for IssueBody."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"body must be a valid JSON string or object: {e}") from e
            if not isinstance(parsed, dict):
                raise ValueError("body JSON string must decode to an object, not a list or scalar")
            return parsed
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "issue_type": "feature",
                    "title": "Add structured issue creation",
                    "priority": "medium",
                    "scope": "mcp-server",
                    "body": {"problem": "The create_issue tool lacks validation."},
                },
                {
                    "issue_type": "bug",
                    "title": "Login fails on Windows when username contains spaces",
                    "priority": "high",
                    "scope": "platform",
                    "body": {
                        "problem": "Login fails with 500 error.",
                        "expected": "Redirect to dashboard.",
                        "actual": "500 Internal Server Error.",
                        "context": "Windows 11, Python 3.13.",
                        "steps_to_reproduce": "1. Enter username with space\n2. Click Login",
                        "related_docs": ["docs/development/issue149/research.md"],
                    },
                    "is_epic": False,
                    "parent_issue": 91,
                    "milestone": "v2.0",
                    "assignees": ["alice"],
                },
            ]
        }
    }


class CreateIssueTool(BaseTool):
    """Tool to create a new GitHub issue."""

    name = "create_issue"
    description = "Create a new GitHub issue"
    args_model = CreateIssueInput

    def __init__(
        self,
        manager: GitHubManager,
        issue_config: IssueConfig,
        milestone_config: MilestoneConfig,
        workflow_config: WorkflowConfig,
    ) -> None:
        self.manager = manager
        self._issue_config = issue_config
        self._milestone_config = milestone_config
        self._workflow_config = workflow_config
        self._renderer = JinjaRenderer(template_dir=get_template_root())

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return inlined JSON Schema without $ref/$defs for VS Code compatibility."""
        return _resolve_schema_refs(CreateIssueInput.model_json_schema())

    def _render_body(self, body: IssueBody, title: str = "") -> str:
        """Render an IssueBody to markdown via issue.md.jinja2."""
        _template_path = "concrete/issue.md.jinja2"
        _template_root = get_template_root()
        _schema = introspect_template_with_inheritance(_template_root, _template_path)
        _parent_chain = getattr(_schema, "parent_chain", [])
        _tier_chain = [(path, "1.0") for path in _parent_chain]
        _version_hash = compute_version_hash("issue", _template_path, _tier_chain)

        return self._renderer.render(
            _template_path,
            format="markdown",
            title=title,
            output_path=None,
            artifact_type="issue",
            version_hash=_version_hash,
            timestamp="",
            problem=body.problem,
            expected=body.expected,
            actual=body.actual,
            context=body.context,
            steps_to_reproduce=body.steps_to_reproduce,
            related_docs=body.related_docs,
        )

    def _assemble_labels(self, params: CreateIssueInput) -> list[str]:
        """Assemble the full label list from structured input fields."""
        issue_cfg = self._issue_config
        workflow_cfg = self._workflow_config

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

    async def execute(self, params: CreateIssueInput, context: NoteContext | None = None) -> ToolResult:
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
            return ToolResult.error(f"Issue validation failed: {e}.")

        try:
            title_safe = normalize_unicode(params.title)
            body_safe = normalize_unicode(self._render_body(params.body, title=params.title))
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
            return ToolResult.text(f"Created issue #{issue['number']}: {issue['title']}")
        except jinja2.TemplateError as e:
            return ToolResult.error(
                f"Body rendering failed: {e}. "
                "Check that issue.md.jinja2 exists in the templates directory."
            )
        except ValueError as e:
            return ToolResult.error(f"Label assembly failed: {e}.")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class GetIssueInput(BaseModel):
    """Input for GetIssueTool."""

    issue_number: int = Field(..., description="The issue number to retrieve")


class GetIssueTool(BaseTool):
    """Tool to get issue details."""

    name = "get_issue"
    description = "Get detailed information about a specific GitHub issue"
    args_model = GetIssueInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: GetIssueInput, context: NoteContext | None = None) -> ToolResult:
        try:
            issue = self.manager.get_issue(params.issue_number)

            assignees_str = ", ".join(a.login for a in issue.assignees) or "none"
            labels_str = ", ".join(label.name for label in issue.labels) or "none"
            milestone_str = issue.milestone.title if issue.milestone else "none"

            return ToolResult.text(
                f"## Issue #{issue.number}: {issue.title}\n\n"
                f"**State:** {issue.state}\n"
                f"**Labels:** {labels_str}\n"
                f"**Assignees:** {assignees_str}\n"
                f"**Milestone:** {milestone_str}\n"
                f"**Created:** {issue.created_at.isoformat()}\n\n"
                f"{issue.body}"
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))


class ListIssuesInput(BaseModel):
    """Input for ListIssuesTool."""

    state: IssueState | None = Field(default=None, description="Filter by issue state")
    labels: list[str] | None = Field(default=None, description="Filter by labels")


class ListIssuesTool(BaseTool):
    """Tool to list issues."""

    name = "list_issues"
    description = "List GitHub issues with optional filtering by state and labels"
    args_model = ListIssuesInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: ListIssuesInput, context: NoteContext | None = None) -> ToolResult:
        try:
            state_str = params.state
            issues = self.manager.list_issues(state=state_str or "open", labels=params.labels)
            if not issues:
                return ToolResult.text("No issues found.")

            summary = "\n".join(
                [f"#{issue.number} {issue.title} ({issue.state})" for issue in issues]
            )
            return ToolResult.text(f"Found {len(issues)} issues:\n{summary}")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class UpdateIssueInput(BaseModel):
    """Input for UpdateIssueTool."""

    issue_number: int = Field(..., description="Issue number to update")
    title: str | None = Field(default=None, description="New title")
    body: str | None = Field(default=None, description="Updated description")
    state: IssueState | None = Field(default=None, description="Target state")
    labels: list[str] | None = Field(default=None, description="Replace labels with this list")
    milestone: int | None = Field(default=None, description="Milestone number to assign")
    assignees: list[str] | None = Field(
        default=None, description="Replace assignees with this list"
    )


class UpdateIssueTool(BaseTool):
    """Tool to update an issue."""

    name = "update_issue"
    description = "Update title, body, state, labels, milestone, or assignees for an issue"
    args_model = UpdateIssueInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: UpdateIssueInput, context: NoteContext | None = None) -> ToolResult:
        try:
            self.manager.update_issue(
                issue_number=params.issue_number,
                title=params.title,
                body=params.body,
                state=params.state,
                labels=params.labels,
                milestone=params.milestone,
                assignees=params.assignees,
            )
            return ToolResult.text(f"Updated issue #{params.issue_number}")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class CloseIssueInput(BaseModel):
    """Input for CloseIssueTool."""

    issue_number: int = Field(..., description="The issue number to close")
    comment: str | None = Field(default=None, description="Optional comment to add before closing")


class CloseIssueTool(BaseTool):
    """Tool to close an issue."""

    name = "close_issue"
    description = "Close a GitHub issue with optional comment"
    args_model = CloseIssueInput

    def __init__(self, manager: GitHubManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: CloseIssueInput, context: NoteContext | None = None) -> ToolResult:
        try:
            self.manager.close_issue(params.issue_number, comment=params.comment)
            return ToolResult.text(f"Closed issue #{params.issue_number}")
        except ExecutionError as e:
            return ToolResult.error(str(e))
