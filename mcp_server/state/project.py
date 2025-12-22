# mcp_server/state/project.py
"""
Project initialization DTOs.

Type-safe data structures for project/milestone/sub-issue management via GitHub API.
Used by InitializeProjectTool to create reproducible project structures.

@layer: DTOs (MCP Server State)
@dependencies: [pydantic]
@responsibilities: [project spec validation, metadata persistence, dependency graph]
"""
# Standard library
from typing import Literal

# Third-party
from pydantic import BaseModel, Field, model_validator


__all__ = [
    "PhaseSpec",
    "ProjectSpec",
    "SubIssueMetadata",
    "ProjectMetadata",
    "ProjectSummary",
    "ValidationResult",
    "ValidationError",
]


class PhaseSpec(BaseModel):
    """
    Specification for a single phase in project initialization.

    Used as input to initialize_project() to define sub-issue structure.

    Attributes:
        phase_id: Unique phase identifier (A, B, C, 0, etc.)
        title: Phase title for GitHub issue
        depends_on: Phase IDs this phase depends on (empty = no dependencies)
        blocks: Phase IDs blocked by this phase (auto-calculated if empty)
        labels: Initial GitHub labels (default: ["phase:red"])
    """

    phase_id: str = Field(..., description="Unique phase identifier", min_length=1)
    title: str = Field(..., description="Phase title for GitHub issue", min_length=1)
    depends_on: list[str] = Field(
        default_factory=list,
        description="Phase IDs this phase depends on"
    )
    blocks: list[str] = Field(
        default_factory=list,
        description="Phase IDs blocked by this phase"
    )
    labels: list[str] = Field(
        default_factory=lambda: ["phase:red"],
        description="Initial GitHub labels"
    )

    @model_validator(mode="after")
    def validate_no_self_dependency(self) -> "PhaseSpec":
        """Ensure phase doesn't depend on itself."""
        if self.phase_id in self.depends_on:
            raise ValueError(f"Phase {self.phase_id} cannot depend on itself")
        if self.phase_id in self.blocks:
            raise ValueError(f"Phase {self.phase_id} cannot block itself")
        return self


class ProjectSpec(BaseModel):
    """
    Specification for project initialization.

    Complete input for initialize_project() tool to create GitHub structure.

    Attributes:
        project_title: Title for milestone and parent issue
        phases: List of phases to create as sub-issues
        parent_issue_number: Tracker issue number (e.g., 18)
        auto_create_branches: Create feature branches immediately (default: False)
        enforce_dependencies: Enable PolicyEngine checks (default: True)
        force_create_parent: Skip duplicate detection, always create new parent
    """

    project_title: str = Field(..., description="Title for milestone and parent issue")
    phases: list[PhaseSpec] = Field(
        ...,
        description="List of phases to create as sub-issues"
    )
    parent_issue_number: int | None = Field(
        default=None,
        description="Tracker issue number (if None, creates new parent issue)",
        gt=0
    )
    auto_create_branches: bool = Field(
        default=False,
        description="Create feature branches immediately"
    )
    enforce_dependencies: bool = Field(
        default=True,
        description="Enable PolicyEngine dependency checks"
    )
    force_create_parent: bool = Field(
        default=False,
        description="Skip duplicate detection when creating parent issue"
    )

    @model_validator(mode="after")
    def validate_unique_phase_ids(self) -> "ProjectSpec":
        """Ensure all phase IDs are unique."""
        phase_ids = [phase.phase_id for phase in self.phases]
        if len(phase_ids) != len(set(phase_ids)):
            duplicates = [pid for pid in phase_ids if phase_ids.count(pid) > 1]
            raise ValueError(f"Duplicate phase IDs: {set(duplicates)}")
        return self

    @model_validator(mode="after")
    def validate_dependencies_exist(self) -> "ProjectSpec":
        """Ensure all dependency references point to existing phases."""
        phase_ids = {phase.phase_id for phase in self.phases}
        for phase in self.phases:
            for dep in phase.depends_on:
                if dep not in phase_ids:
                    raise ValueError(
                        f"Phase {phase.phase_id} depends on non-existent phase {dep}"
                    )
            for blocked in phase.blocks:
                if blocked not in phase_ids:
                    raise ValueError(
                        f"Phase {phase.phase_id} blocks non-existent phase {blocked}"
                    )
        return self


class SubIssueMetadata(BaseModel):
    """
    Metadata for a single sub-issue.

    Persisted in .st3/projects.json after project initialization.

    Attributes:
        issue_number: GitHub issue number
        url: GitHub issue URL
        depends_on: Phase IDs this phase depends on
        blocks: Phase IDs blocked by this phase
        status: Current issue status (synced from GitHub)
    """

    issue_number: int = Field(..., description="GitHub issue number", gt=0)
    url: str = Field(..., description="GitHub issue URL")
    depends_on: list[str] = Field(
        default_factory=list,
        description="Phase IDs this phase depends on"
    )
    blocks: list[str] = Field(
        default_factory=list,
        description="Phase IDs blocked by this phase"
    )
    status: Literal["open", "in-progress", "closed"] = Field(
        default="open",
        description="Current issue status"
    )


class ProjectMetadata(BaseModel):
    """
    Metadata persisted to .st3/projects.json.

    Local cache of project structure (GitHub API is SSOT).

    Attributes:
        project_id: Unique project identifier (e.g., "project-18")
        parent_issue: Parent issue info (number and URL)
        milestone_id: GitHub milestone ID
        phases: Mapping of phase_id to sub-issue metadata
    """

    project_id: str = Field(..., description="Unique project identifier")
    parent_issue: dict[str, int | str] = Field(
        ...,
        description="Parent issue info: {'number': int, 'url': str}"
    )
    milestone_id: int = Field(..., description="GitHub milestone ID", gt=0)
    phases: dict[str, SubIssueMetadata] = Field(
        ...,
        description="Mapping of phase_id to sub-issue metadata"
    )


class ProjectSummary(BaseModel):
    """
    Result returned by initialize_project tool.

    Summary of created GitHub structure for agent/user feedback.

    Attributes:
        project_id: Unique project identifier
        milestone_id: Created milestone ID
        parent_issue: Parent issue info (number and URL)
        sub_issues: Mapping of phase_id to sub-issue metadata
        dependency_graph: Adjacency list (phase_id → list of blocked phases)
    """

    project_id: str = Field(..., description="Unique project identifier")
    milestone_id: int = Field(..., description="Created milestone ID", gt=0)
    parent_issue: dict[str, int | str] = Field(
        ...,
        description="Parent issue info: {'number': int, 'url': str}"
    )
    sub_issues: dict[str, SubIssueMetadata] = Field(
        ...,
        description="Mapping of phase_id to sub-issue metadata"
    )
    dependency_graph: dict[str, list[str]] = Field(
        ...,
        description="Adjacency list: phase_id → list of blocked phase_ids"
    )


class ValidationError(BaseModel):
    """
    Single validation error from validate_project_structure.

    Attributes:
        type: Error type (missing_issue, circular_dependency, etc.)
        message: Human-readable error description
        phase_id: Phase ID if error is phase-specific
        issue_number: Issue number if error is issue-specific
        details: Additional error context
    """

    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error description")
    phase_id: str | None = Field(default=None, description="Phase ID if phase-specific")
    issue_number: int | None = Field(
        default=None,
        description="Issue number if issue-specific"
    )
    details: dict[str, str | int | list[str]] | None = Field(
        default=None,
        description="Additional error context"
    )


class ValidationResult(BaseModel):
    """
    Result from validate_project_structure tool.

    Reports discrepancies between .st3/projects.json and GitHub API state.

    Attributes:
        valid: True if no errors, False otherwise
        errors: List of validation errors (blocking issues)
        warnings: List of validation warnings (non-blocking)
    """

    valid: bool = Field(..., description="True if no errors")
    errors: list[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    warnings: list[ValidationError] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
