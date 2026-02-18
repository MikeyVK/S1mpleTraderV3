"""Issue management tools."""

import copy
import json
import unicodedata
from typing import Any, Literal

import jinja2
from pydantic import BaseModel, Field, field_validator

from mcp_server.config.contributor_config import ContributorConfig
from mcp_server.config.git_config import GitConfig
from mcp_server.config.issue_config import IssueConfig
from mcp_server.config.label_config import LabelConfig
from mcp_server.config.milestone_config import MilestoneConfig
from mcp_server.config.scope_config import ScopeConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.config.workflow_config import WorkflowConfig
from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

IssueState = Literal["open", "closed", "all"]


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text for safe JSON-RPC transmission.

    Preserves emoji and other Unicode while fixing malformed surrogates.
    """
    # Step 1: Encode to UTF-8 bytes, handling surrogates
    try:
        utf8_bytes = text.encode("utf-8", errors="surrogatepass")
    except UnicodeEncodeError:
        # Fallback: replace bad surrogates
        utf8_bytes = text.encode("utf-8", errors="replace")

    # Step 2: Decode back to string
    normalized = utf8_bytes.decode("utf-8", errors="replace")

    # Step 3: Apply Unicode normalization (NFC = canonical composition)
    return unicodedata.normalize("NFC", normalized)


def _resolve_schema_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline all $ref references in a JSON Schema.

    VS Code / Copilot Chat does not resolve JSON Schema $ref when constructing
    MCP tool call arguments, so the model cannot build nested objects described
    with  body: {"$ref": "#/$defs/IssueBody"}.

    This function resolves all $ref entries by inlining the corresponding
    definition from $defs, producing a fully self-contained schema without
    $defs or $ref.

    Args:
        schema: A JSON Schema dict (typically from model_json_schema()).

    Returns:
        A new schema dict with all $ref references inlined.
    """
    schema = copy.deepcopy(schema)
    defs: dict[str, Any] = schema.pop("$defs", {})

    def _resolve(node: Any) -> Any:  # type: ignore[return]  # noqa: ANN401
        if isinstance(node, dict):
            if "$ref" in node:
                ref_path: str = node["$ref"]  # e.g. "#/$defs/IssueBody"
                def_name = ref_path.split("/")[-1]
                resolved = copy.deepcopy(defs.get(def_name, {}))
                # Merge any sibling keys from the $ref node (e.g. description)
                for k, v in node.items():
                    if k != "$ref":
                        resolved[k] = v
                return _resolve(resolved)
            return {k: _resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_resolve(item) for item in node]
        return node

    return _resolve(schema)  # type: ignore[return-value]


class IssueBody(BaseModel):
    """Structured body for a GitHub issue, rendered via issue.md.jinja2.

    json_schema_extra examples:
    - Minimal: only `problem` provided — all other fields omitted
    - Full: all optional sections populated for a comprehensive report
    """

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

    All fields are validated against project config (issues.yaml, scopes.yaml,
    milestones.yaml, contributors.yaml, git.yaml). No free-form labels accepted —
    labels are assembled internally by CreateIssueTool.

    json_schema_extra examples are below: minimal (required fields only) and full.
    """

    issue_type: str = Field(..., description="Issue type: feature, bug, hotfix, chore, docs, epic")
    title: str = Field(..., description="Issue title (max 72 chars from git.yaml)")
    priority: str = Field(..., description="Priority: critical, high, medium, low, triage")
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
        """Accept a JSON string for body and parse it into a dict for IssueBody.

        The MCP chat interface (Copilot Chat) serializes nested objects as JSON
        strings. Without this coercion every chat call fails with
        'is not of type object'.
        """
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"body must be a valid JSON string or object: {e}") from e
            if not isinstance(parsed, dict):
                raise ValueError("body JSON string must decode to an object, not a list or scalar")
            return parsed
        return v

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v: str) -> str:
        cfg = IssueConfig.from_file()
        if not cfg.has_issue_type(v):
            valid = sorted(e.name for e in cfg.issue_types)
            raise ValueError(f"Unknown issue type: '{v}'. Valid values: {valid}")
        return v

    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v: str) -> str:
        git_cfg = GitConfig.from_file()
        max_len = git_cfg.issue_title_max_length
        if len(v) > max_len:
            raise ValueError(f"Title too long: {len(v)} chars (max {max_len} from git.yaml)")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        cfg = LabelConfig.load()
        valid = {lbl.name.split(":", 1)[1] for lbl in cfg.get_labels_by_category("priority")}
        if v not in valid:
            raise ValueError(f"Unknown priority: '{v}'. Valid values: {sorted(valid)}")
        return v

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        cfg = ScopeConfig.from_file()
        if not cfg.has_scope(v):
            raise ValueError(f"Unknown scope: '{v}'. Valid values: {sorted(cfg.scopes)}")
        return v

    @field_validator("milestone")
    @classmethod
    def validate_milestone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cfg = MilestoneConfig.from_file()
        if not cfg.validate_milestone(v):
            raise ValueError(f"Unknown milestone: '{v}'. Must match a title in milestones.yaml.")
        return v

    @field_validator("assignees")
    @classmethod
    def validate_assignee(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cfg = ContributorConfig.from_file()
        for login in v:
            if not cfg.validate_assignee(login):
                raise ValueError(
                    f"Unknown assignee: '{login}'. Must be listed in contributors.yaml."
                )
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

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()
        self._renderer = JinjaRenderer(template_dir=get_template_root())

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return inlined JSON Schema without $ref/$defs for VS Code compatibility.

        VS Code / Copilot Chat does not resolve $ref when constructing tool
        call arguments, so we inline IssueBody directly into the schema.
        """
        return _resolve_schema_refs(CreateIssueInput.model_json_schema())

    def _render_body(self, body: IssueBody, title: str = "") -> str:
        """Render an IssueBody to markdown via issue.md.jinja2.

        Args:
            body: Structured issue body fields.
            title: Issue title rendered as H1 heading.

        Returns:
            Markdown string with SCAFFOLD metadata as invisible HTML comments.
        """
        return self._renderer.render(
            "concrete/issue.md.jinja2",
            format="markdown",
            title=title,
            output_path="",
            artifact_type="",
            version_hash="",
            timestamp="",
            problem=body.problem,
            expected=body.expected,
            actual=body.actual,
            context=body.context,
            steps_to_reproduce=body.steps_to_reproduce,
            related_docs=body.related_docs,
        )

    def _assemble_labels(self, params: CreateIssueInput) -> list[str]:
        """Assemble the full label list from structured input fields.

        Assembly rules (in order):
          type_label     = "type:epic"                        if is_epic
                         = IssueConfig.get_label(issue_type)  otherwise
          scope_label    = "scope:{scope}"
          priority_label = "priority:{priority}"
          phase_label    = "phase:{first_phase}"              from workflows.yaml
          parent_label   = "parent:{n}"                      if parent_issue is not None
        """
        issue_cfg = IssueConfig.from_file()
        workflow_cfg = WorkflowConfig.from_file()

        # type label
        type_label = "type:epic" if params.is_epic else issue_cfg.get_label(params.issue_type)

        # phase label — derive from first phase of the issue type's workflow
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

    async def execute(self, params: CreateIssueInput) -> ToolResult:
        try:
            title_safe = normalize_unicode(params.title)
            body_safe = normalize_unicode(self._render_body(params.body, title=params.title))
            labels = self._assemble_labels(params)

            issue = self.manager.create_issue(
                title=title_safe,
                body=body_safe,
                labels=labels,
                milestone=params.milestone,
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

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: GetIssueInput) -> ToolResult:
        try:
            issue = self.manager.get_issue(params.issue_number)

            # Formatting helpers
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

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: ListIssuesInput) -> ToolResult:
        try:
            # `IssueState` is a typing.Literal alias, not a runtime type.
            # Pydantic will give us either a string value or None.
            state_str = params.state
            issues = self.manager.list_issues(state=state_str or "open", labels=params.labels)
            if not issues:
                return ToolResult.text("No issues found.")

            summary = "\n".join([f"#{i.number} {i.title} ({i.state})" for i in issues])
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

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: UpdateIssueInput) -> ToolResult:
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

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: CloseIssueInput) -> ToolResult:
        try:
            self.manager.close_issue(params.issue_number, comment=params.comment)
            return ToolResult.text(f"Closed issue #{params.issue_number}")
        except ExecutionError as e:
            return ToolResult.error(str(e))
