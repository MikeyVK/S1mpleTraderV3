"""Project management workflow tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.state.project import PhaseSpec, ProjectSpec
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
