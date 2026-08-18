# mcp_server/schemas/tool_outputs.py
# template=schema version=74378193 created=2026-06-12T20:49Z updated=2026-06-12T21:00Z
"""Base tool output schemas.

@layer: Schemas
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseToolOutput(BaseModel):
    """Base class for all structured tool outputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool = True

    error_message: str | None = None
    post_tool_instruction: str | None = None


class AutoFixOutput(BaseToolOutput):
    """Output for AutoFixTool."""

    modified_files: list[str] = Field(
        default_factory=list, description="List of files modified by the tool"
    )
    modified_files_count: int = Field(default=0, description="Count of modified files")
    formatted_modified_files: str = Field(
        default="", description="Pre-formatted bullet list of modified files"
    )
    gates_executed: list[str] = Field(
        default_factory=list, description="List of quality gates executed"
    )
    gates_executed_count: int = Field(default=0, description="Count of executed gates")


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class HealthCheckOutput(BaseToolOutput):
    status: HealthStatus = HealthStatus.HEALTHY
    reason: str | None = None
    version: str
    pid: int
    platform: str
    uptime_seconds: float


class RestartServerOutput(BaseToolOutput):
    reason: str
    pid: int
    timestamp: float
    iso_time: str


class GateTransitionOutput(BaseToolOutput):
    """Base class for workflows verifying gates during phase or cycle transitions."""

    branch: str
    passing_gates: list[str] = Field(default_factory=list)
    skipped_gates: list[str] = Field(default_factory=list)
    passing_gates_count: int = 0
    skipped_gates_count: int = 0


class CycleTransitionOutput(GateTransitionOutput):
    from_cycle: int | None = None
    to_cycle: int
    total_cycles: int
    cycle_name: str


class ForceCycleTransitionOutput(CycleTransitionOutput):
    skip_reason: str
    human_approval_message: str


class GetWorkContextOutput(BaseToolOutput):
    current_branch: str
    workflow_name: str
    phase: str
    issue_number: int | None = None
    parent_branch: str | None = None
    current_cycle: int | None = None
    sub_phase: str | None = None
    phase_source: str
    phase_confidence: str
    sub_role_hint: str
    phase_instructions: str
    handover_template: str | None = None
    invalid_phase_warning: str | None = None


class InitializeProjectOutput(BaseToolOutput):
    issue_number: int
    workflow_name: str
    branch: str
    initial_phase: str
    parent_branch: str | None = None
    required_phases: list[str] = Field(default_factory=list)
    execution_mode: str
    files_created: list[str] = Field(default_factory=list)


class PhaseTaskDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    title: str
    status: str


class PhaseDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    status: str
    tasks: list[PhaseTaskDTO] = Field(default_factory=list)


class ProjectPlanOutput(BaseToolOutput):
    issue_number: int
    workflow_name: str
    phases: list[PhaseDTO] = Field(default_factory=list)


class PlannedCycleSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    cycle_number: int
    deliverables_count: int


class PlanningDeliverablesOutput(BaseToolOutput):
    issue_number: int
    total_cycles: int
    total_deliverables: int
    cycles: list[PlannedCycleSummary] = Field(default_factory=list)


class BranchPairOutput(BaseToolOutput):
    """Base class for Git operations comparing or merging two branches."""

    source_branch: str
    target_branch: str


class BranchDetailDTO(BaseModel):
    """Detail for a single Git branch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    is_current: bool
    commit_hash: str | None = None
    upstream: str | None = None


class GitListBranchesOutput(BaseToolOutput):
    """Output for GitListBranchesTool."""

    current_branch: str
    branches: list[BranchDetailDTO] = Field(default_factory=list)
    branches_count: int = 0


class GitDiffOutput(BranchPairOutput):
    """Output for GitDiffTool."""

    stats: str
    files_changed: int | None = None
    insertions: int | None = None
    deletions: int | None = None


class GetParentBranchOutput(BaseToolOutput):
    """Output for GetParentBranchTool."""

    branch: str
    parent_branch: str | None = None


class CheckMergeOutput(BaseToolOutput):
    """Output for CheckMergeTool."""

    merge_sha: str
    is_ancestor: bool


class GitStatusOutput(BaseToolOutput):
    """Output for GitStatusTool."""

    branch: str
    is_clean: bool
    modified_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    modified_count: int
    untracked_count: int


class CreateBranchOutput(BaseToolOutput):
    """Output for CreateBranchTool."""

    branch_name: str
    branch_type: str
    base_branch: str


class GitCommitOutput(BaseToolOutput):
    """Output for GitCommitTool."""

    commit_hash: str
    branch: str
    workflow_phase: str
    sub_phase: str | None = None
    cycle_number: int | None = None
    commit_type: str
    files: list[str] = Field(default_factory=list)


class GitRestoreOutput(BaseToolOutput):
    """Output for GitRestoreTool."""

    files: list[str] = Field(default_factory=list)
    source: str
    files_count: int = 0


class GitCheckoutOutput(BaseToolOutput):
    """Output for GitCheckoutTool."""

    branch: str
    previous_branch: str | None = None
    current_phase: str
    parent_branch: str | None = None


class GitPushOutput(BaseToolOutput):
    """Output for GitPushTool."""

    branch: str
    set_upstream: bool
    new_upstream_created: bool = False


class GitMergeOutput(BranchPairOutput):
    """Output for GitMergeTool."""

    pass


class GitDeleteBranchOutput(BaseToolOutput):
    """Output for GitDeleteBranchTool."""

    branch: str
    local_status: str
    remote_status: str


class GitStashOutput(BaseToolOutput):
    """Output for GitStashTool."""

    action: str
    message: str | None = None
    stashes: list[str] = Field(default_factory=list)


class GitFetchPullOutput(BaseToolOutput):
    """Base class for Git remote operations returning output."""

    remote: str
    raw_output: str


class GitFetchOutput(GitFetchPullOutput):
    """Output for GitFetchTool."""

    prune: bool


class GitPullOutput(GitFetchPullOutput):
    """Output for GitPullTool."""

    rebase: bool


class GitHubObjectOutput(BaseToolOutput):
    """Base class for GitHub resources that have a number and title."""

    number: int
    title: str


class IssueOutput(GitHubObjectOutput):
    """Output for GitHub Issue creation, retrieval, and updates."""

    state: str
    milestone_title: str = "None"
    assignees_summary: str = "Unassigned"
    html_url: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    closed_at: str | None = None
    author: str


class CloseIssueOutput(BaseToolOutput):
    """Output for CloseIssueTool."""

    issue_number: int


class IssueSummaryDTO(BaseModel):
    """Summary representation of an issue for listing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int
    title: str
    state: str
    html_url: str
    labels: list[str] = Field(default_factory=list)
    assignees_summary: str = "Unassigned"
    created_at: str


class ListIssuesOutput(BaseToolOutput):
    """Output for ListIssuesTool."""

    issues_count: int
    issues: list[IssueSummaryDTO] = Field(default_factory=list)


class PROutput(GitHubObjectOutput):
    """Output for PR creation and retrieval."""

    html_url: str
    state: str
    base_ref: str
    head_ref: str
    merged_at: str | None = None
    merge_sha: str | None = None
    body: str = ""


class MergePROutput(BaseToolOutput):
    """Output for MergePRTool."""

    pr_number: int
    merge_sha: str
    merge_method: str


class PRSummaryDTO(BaseModel):
    """Summary representation of a PR for listing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int
    title: str
    state: str
    html_url: str
    base_ref: str
    head_ref: str


class ListPRsOutput(BaseToolOutput):
    """Output for ListPRsTool."""

    prs_count: int
    pull_requests: list[PRSummaryDTO] = Field(default_factory=list)


class LabelOutputModel(BaseModel):
    """Output representation of a single label."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    color: str
    description: str | None = None


class ListLabelsOutput(BaseToolOutput):
    """Output for ListLabelsTool."""

    total_labels: int
    labels: list[LabelOutputModel] = Field(default_factory=list)


class CreateLabelOutput(BaseToolOutput):
    """Output for CreateLabelTool."""

    label_name: str
    color: str


class DeleteLabelOutput(BaseToolOutput):
    """Output for DeleteLabelTool."""

    label_name: str


class LabelOperationOutput(BaseToolOutput):
    """Output for AddLabelsTool and RemoveLabelsTool."""

    issue_number: int
    labels: list[str] = Field(default_factory=list)
    formatted_labels: str = ""


class MilestoneSummaryDTO(BaseModel):
    """Summary representation of a milestone."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int
    title: str
    state: str


class ListMilestonesOutput(BaseToolOutput):
    """Output for ListMilestonesTool."""

    total_milestones: int
    milestones: list[MilestoneSummaryDTO] = Field(default_factory=list)


class MilestoneOutput(GitHubObjectOutput):
    """Output for CreateMilestoneTool and CloseMilestoneTool."""

    state: str


class PhaseTransitionOutput(GateTransitionOutput):
    """Output for TransitionPhaseTool."""

    from_phase: str
    to_phase: str
    skipped_gates_warning: str = ""
    passing_gates_info: str = ""


class ForcePhaseTransitionOutput(PhaseTransitionOutput):
    """Output for ForcePhaseTransitionTool."""

    skip_reason: str
    human_approval_message: str


class ScaffoldArtifactOutput(BaseToolOutput):
    """Output for ScaffoldArtifactTool."""

    artifact_type: str
    name: str
    files_created: list[str] = Field(default_factory=list)
    formatted_files_created: str = ""
    schema_info: str = ""
    validation_schema: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    provided_fields: list[str] = Field(default_factory=list)


class ScaffoldSchemaOutput(BaseToolOutput):
    """Output for ScaffoldSchemaTool."""

    artifact_type: str
    schema_data: dict[str, Any]


class GateResultDTO(BaseModel):
    """Single gate run result."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    passed: bool
    status: str
    score: str | None = None
    details: str = ""


class RunQualityGatesOutput(BaseToolOutput):
    """Output for RunQualityGatesTool."""

    overall_pass: bool
    scope: str
    file_count: int
    gates: list[GateResultDTO] = Field(default_factory=list)


class TestFailureDTO(BaseModel):
    """DTO for a single test failure."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    test_id: str
    location: str
    short_reason: str
    traceback: str = ""
    is_collection_error: bool = False


class RunTestsOutput(BaseToolOutput):
    """Output for RunTestsTool."""

    exit_code: int
    passed_count: int
    failed_count: int
    skipped_count: int
    errors_count: int
    summary_line: str
    failures: list[TestFailureDTO] = Field(default_factory=list)
    coverage_pct: float | None = None
    lf_cache_was_empty: bool = False
    stderr: str = ""


class SafeEditOutput(BaseToolOutput):
    """Output for SafeEditTool."""

    path: str
    passed: bool
    issues: str | None = None
    mode: str
    written: bool
    diff: str | None = None
    has_diff: bool = False


class TemplateValidationErrorDTO(BaseModel):
    """Single template validation error."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    severity: str
    message: str


class TemplateValidationOutput(BaseToolOutput):
    """Output for TemplateValidationTool."""

    passed: bool
    errors_count: int
    errors: list[TemplateValidationErrorDTO] = Field(default_factory=list)
