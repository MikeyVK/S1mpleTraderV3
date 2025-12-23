"""Project management workflow tools."""
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.managers.dependency_graph_validator import DependencyGraphValidator
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.state.project import (
    PhaseSpec,
    ProjectMetadata,
    ProjectSpec,
    ValidationError as ProjectValidationError,
    ValidationResult,
)
from mcp_server.tools.base import BaseTool, ToolResult


class InitializeProjectInput(BaseModel):
    """Input for InitializeProjectTool."""

    project_title: str = Field(
        ...,
        description="Title for milestone and parent issue"
    )
    phases: list[dict[str, Any]] = Field(
        ...,
        description="List of phase specifications with phase_id, title, "
                   "depends_on, blocks, labels"
    )
    parent_issue_number: int | None = Field(
        default=None,
        description="Existing tracker issue number (if None, creates new)",
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


class InitializeProjectTool(BaseTool):
    """Tool to initialize a project with phases and dependency management.

    Creates:
    - GitHub milestone
    - Parent issue (or uses existing)
    - Sub-issues for each phase
    - Updates parent issue with sub-issue links
    - Persists metadata to .st3/projects.json

    Validates dependency graph for cycles before creating GitHub resources.
    """

    name = "initialize_project"
    description = (
        "Initialize a project with phases, dependencies, and GitHub structure. "
        "Creates milestone, parent issue, and sub-issues with dependency validation."
    )
    args_model = InitializeProjectInput

    def __init__(self, manager: ProjectManager | None = None) -> None:
        """Initialize tool with ProjectManager.

        Args:
            manager: ProjectManager instance (injected for testing)
        """
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool input."""
        return super().input_schema

    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        """Execute project initialization.

        Args:
            params: Project initialization parameters

        Returns:
            ToolResult with ProjectSummary or error message
        """
        # Validate manager configured first for type narrowing
        if self.manager is None:
            return self._error_result(
                "ProjectManager not configured. "
                "GitHub adapter and workspace root required."
            )

        try:
            # Convert and validate inputs
            phase_specs = self._convert_phase_specs(params.phases)
            project_spec = self._create_project_spec(params, phase_specs)

            # Execute initialization
            summary = self.manager.initialize_project(project_spec)

            # Format success response
            result_text = self._format_summary(summary)
            return ToolResult.text(result_text)

        except (ValidationError, ExecutionError) as e:
            error_type = "Validation" if isinstance(e, ValidationError) else "Execution"
            return self._error_result(f"{error_type} error: {e}")
        except (ValueError, TypeError) as e:
            return self._error_result(f"Invalid input: {e}")
        except (IOError, OSError) as e:
            return self._error_result(f"File system error: {e}")
        except RuntimeError as e:
            return self._error_result(f"Runtime error: {e}")

    def _convert_phase_specs(
        self, phase_dicts: list[dict[str, Any]]
    ) -> list[PhaseSpec]:
        """Convert dict phases to PhaseSpec objects.

        Args:
            phase_dicts: List of phase dictionaries

        Returns:
            List of PhaseSpec objects

        Raises:
            ValueError: If phase specification is invalid
        """
        phase_specs = []
        for phase_dict in phase_dicts:
            phase_spec = PhaseSpec(**phase_dict)
            phase_specs.append(phase_spec)
        return phase_specs

    def _create_project_spec(
        self, params: InitializeProjectInput, phase_specs: list[PhaseSpec]
    ) -> ProjectSpec:
        """Create ProjectSpec from input parameters.

        Args:
            params: Tool input parameters
            phase_specs: Validated phase specifications

        Returns:
            ProjectSpec object

        Raises:
            ValidationError: If project specification is invalid
        """
        return ProjectSpec(
            project_title=params.project_title,
            phases=phase_specs,
            parent_issue_number=params.parent_issue_number,
            auto_create_branches=params.auto_create_branches,
            enforce_dependencies=params.enforce_dependencies,
            force_create_parent=params.force_create_parent,
        )

    def _error_result(self, message: str) -> ToolResult:
        """Create error ToolResult.

        Args:
            message: Error message

        Returns:
            ToolResult with error
        """
        return ToolResult.error(message)

    def _format_summary(self, summary: Any) -> str:
        """Format ProjectSummary for display.

        Args:
            summary: ProjectSummary object

        Returns:
            Formatted string with project details
        """
        lines = [
            f"# Project Initialized: {summary.project_id}",
            "",
            f"**Milestone ID:** {summary.milestone_id}",
            f"**Parent Issue:** #{summary.parent_issue['number']} - "
            f"{summary.parent_issue['url']}",
            "",
            "## Sub-Issues Created:",
            "",
        ]

        for phase_id, metadata in summary.sub_issues.items():
            lines.append(
                f"- **[{phase_id}]** #{metadata.issue_number} - "
                f"{metadata.url}"
            )
            if metadata.depends_on:
                lines.append(
                    f"  - Depends on: {', '.join(metadata.depends_on)}"
                )
            if metadata.blocks:
                lines.append(f"  - Blocks: {', '.join(metadata.blocks)}")

        lines.extend([
            "",
            "## Dependency Graph:",
            "",
        ])

        for phase_id, blocks in summary.dependency_graph.items():
            if blocks:
                lines.append(f"- **{phase_id}** blocks: {', '.join(blocks)}")
            else:
                lines.append(f"- **{phase_id}** (no blocks)")

        lines.extend([
            "",
            "**Metadata persisted to:** `.st3/projects.json`",
        ])

        return "\n".join(lines)


class ValidateProjectStructureInput(BaseModel):
    """Input for ValidateProjectStructureTool."""

    project_id: str = Field(
        ...,
        description="Project identifier to validate (e.g., 'project-18')"
    )


class ValidateProjectStructureTool(BaseTool):
    """Tool to validate project structure against GitHub API.

    Validates:
    - Milestone exists in GitHub
    - All sub-issues exist in GitHub
    - No circular dependencies in dependency graph
    - Issue labels match expected phase labels (warning)
    - Issue state matches metadata (warning)

    Reads .st3/projects.json and queries GitHub API for comparison.
    """

    name = "validate_project_structure"
    description = (
        "Validate project structure by comparing .st3/projects.json with GitHub API. "
        "Detects missing issues, circular dependencies, and label mismatches."
    )
    args_model = ValidateProjectStructureInput

    def __init__(
        self,
        github_adapter: Any | None = None,
        workspace_root: Path | None = None
    ) -> None:
        """Initialize tool with GitHub adapter and workspace root.

        Args:
            github_adapter: GitHub API adapter (injected for testing)
            workspace_root: Path to workspace root (for .st3/projects.json)
        """
        self.github_adapter = github_adapter
        self.workspace_root = workspace_root

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return JSON schema for tool input."""
        return super().input_schema

    async def execute(self, params: ValidateProjectStructureInput) -> ToolResult:
        """Execute project structure validation.

        Args:
            params: Validation parameters with project_id

        Returns:
            ToolResult with ValidationResult (JSON) or error message
        """
        # Convert dict to pydantic model if needed
        if isinstance(params, dict):
            params = ValidateProjectStructureInput(**params)

        # Validate dependencies configured
        if self.github_adapter is None or self.workspace_root is None:
            return self._error_result(
                "GitHub adapter and workspace root not configured. "
                "Cannot validate project structure."
            )

        try:
            # Load project metadata
            metadata = self._load_project_metadata(params.project_id)

            # Validate against GitHub
            errors: list[ProjectValidationError] = []
            warnings: list[ProjectValidationError] = []

            # Check 1: Milestone exists
            milestone_error = self._validate_milestone(metadata.milestone_id)
            if milestone_error:
                errors.append(milestone_error)

            # Check 2: Parent issue exists
            parent_error = self._validate_parent_issue(metadata.parent_issue)
            if parent_error:
                errors.append(parent_error)

            # Check 3: All sub-issues exist + collect warnings
            issue_errors, issue_warnings = self._validate_sub_issues(metadata)
            errors.extend(issue_errors)
            warnings.extend(issue_warnings)

            # Check 4: No circular dependencies
            cycle_error = self._validate_no_cycles(metadata)
            if cycle_error:
                errors.append(cycle_error)

            # Build result
            result = ValidationResult(
                valid=not errors,  # Use implicit booleaness
                errors=errors,
                warnings=warnings
            )

            return ToolResult.text(result.model_dump_json(indent=2))

        except (FileNotFoundError, KeyError) as e:
            return self._error_result(str(e))
        except Exception as e:
            return self._error_result(f"Validation error: {e}")

    def _load_project_metadata(self, project_id: str) -> ProjectMetadata:
        """Load project metadata from .st3/projects.json.

        Args:
            project_id: Project identifier

        Returns:
            ProjectMetadata for the project

        Raises:
            FileNotFoundError: If .st3/projects.json not found
            KeyError: If project_id not in file
        """
        assert self.workspace_root is not None
        projects_file = self.workspace_root / ".st3" / "projects.json"

        if not projects_file.exists():
            raise FileNotFoundError(
                f"Project metadata not found: {projects_file}. "
                f"Run initialize_project first."
            )

        data = json.loads(projects_file.read_text())
        if project_id not in data.get("projects", {}):
            raise KeyError(
                f"Project '{project_id}' not found in {projects_file}. "
                f"Available projects: {list(data.get('projects', {}).keys())}"
            )

        return ProjectMetadata(**data["projects"][project_id])

    def _validate_milestone(self, milestone_id: int) -> ProjectValidationError | None:
        """Validate milestone exists in GitHub.

        Args:
            milestone_id: Milestone ID to check

        Returns:
            ValidationError if milestone not found, None otherwise
        """
        try:
            assert self.github_adapter is not None
            self.github_adapter.get_milestone(milestone_id)
            return None
        except Exception:  # pylint: disable=broad-exception-caught
            return ProjectValidationError(
                type="missing_milestone",
                message=f"Milestone #{milestone_id} not found in GitHub",
                details={"milestone_id": milestone_id}
            )

    def _validate_parent_issue(
        self, parent_issue: dict[str, int | str]
    ) -> ProjectValidationError | None:
        """Validate parent issue exists in GitHub.

        Args:
            parent_issue: Parent issue metadata (number + url)

        Returns:
            ValidationError if parent not found, None otherwise
        """
        try:
            assert self.github_adapter is not None
            issue_number = parent_issue["number"]
            self.github_adapter.get_issue(issue_number)
            return None
        except Exception:  # pylint: disable=broad-exception-caught
            return ProjectValidationError(
                type="missing_parent_issue",
                message=f"Parent issue #{parent_issue['number']} not found in GitHub",
                issue_number=int(parent_issue["number"]),
                details={"url": str(parent_issue["url"])}
            )

    def _validate_sub_issues(
        self, metadata: ProjectMetadata
    ) -> tuple[list[ProjectValidationError], list[ProjectValidationError]]:
        """Validate all sub-issues exist in GitHub.

        Args:
            metadata: Project metadata with sub-issues

        Returns:
            Tuple of (errors, warnings)
        """
        errors: list[ProjectValidationError] = []
        warnings: list[ProjectValidationError] = []

        for phase_id, sub_issue in metadata.phases.items():
            try:
                assert self.github_adapter is not None
                github_issue = self.github_adapter.get_issue(sub_issue.issue_number)

                # Check state mismatch (warning)
                if github_issue["state"] != sub_issue.status:
                    error_type = (
                        "state_mismatch"
                        if github_issue["state"] == "open"
                        else "issue_closed_early"
                    )
                    warnings.append(ProjectValidationError(
                        type=error_type,
                        message=(
                            f"Phase {phase_id} (#{sub_issue.issue_number}): "
                            f"GitHub state is '{github_issue['state']}', "
                            f"metadata shows '{sub_issue.status}'"
                        ),
                        phase_id=phase_id,
                        issue_number=sub_issue.issue_number,
                        details={
                            "github_state": github_issue["state"],
                            "metadata_status": sub_issue.status,
                            "blocks": sub_issue.blocks
                        }
                    ))

                # Check label mismatch (warning)
                github_labels = [
                    label["name"] for label in github_issue.get("labels", [])
                ]
                expected_label = "phase:red"  # Simplified - infer from status
                if expected_label not in github_labels and github_labels:
                    warnings.append(ProjectValidationError(
                        type="label_mismatch",
                        message=(
                            f"Phase {phase_id} (#{sub_issue.issue_number}): "
                            f"Expected label '{expected_label}', "
                            f"found {github_labels}"
                        ),
                        phase_id=phase_id,
                        issue_number=sub_issue.issue_number,
                        details={
                            "expected": expected_label,
                            "actual": github_labels
                        }
                    ))

            except Exception:  # pylint: disable=broad-exception-caught
                errors.append(ProjectValidationError(
                    type="missing_issue",
                    message=(
                        f"Phase {phase_id}: "
                        f"Issue #{sub_issue.issue_number} not found in GitHub"
                    ),
                    phase_id=phase_id,
                    issue_number=sub_issue.issue_number,
                    details={"url": sub_issue.url}
                ))

        return errors, warnings

    def _validate_no_cycles(
        self, metadata: ProjectMetadata
    ) -> ProjectValidationError | None:
        """Validate dependency graph has no cycles.

        Args:
            metadata: Project metadata with dependency graph

        Returns:
            ValidationError if cycle detected, None otherwise
        """
        # Build PhaseSpec list from metadata
        phases = [
            PhaseSpec(
                phase_id=phase_id,
                title=f"Phase {phase_id}",
                depends_on=sub_issue.depends_on,
                blocks=sub_issue.blocks
            )
            for phase_id, sub_issue in metadata.phases.items()
        ]

        # Use DependencyGraphValidator
        validator = DependencyGraphValidator()
        is_valid, cycle = validator.validate_acyclic(phases)

        if not is_valid and cycle:
            return ProjectValidationError(
                type="circular_dependency",
                message=f"Circular dependency detected: {' → '.join(cycle)}",
                details={"cycle": cycle}
            )

        return None

    def _error_result(self, message: str) -> ToolResult:
        """Create error ToolResult.

        Args:
            message: Error message

        Returns:
            ToolResult with error
        """
        return ToolResult.error(message)
