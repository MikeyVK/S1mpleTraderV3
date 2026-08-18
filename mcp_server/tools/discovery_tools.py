"""Discovery tools for AI self-orientation."""

# pyright: reportIncompatibleMethodOverride=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict

from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import StateNotFoundError
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.schemas import WorkphasesConfig
from mcp_server.schemas.tool_outputs import GetWorkContextOutput
from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import NoteContext

if TYPE_CHECKING:
    from mcp_server.config.schemas.contracts_config import ContractsConfig
    from mcp_server.core.interfaces import IContextLoadedWriter
    from mcp_server.managers.workflow_status_resolver import WorkflowStatusResolver


class GetWorkContextInput(BaseModel):
    """Input for GetWorkContextTool."""

    model_config = ConfigDict(extra="forbid")


class GetWorkContextTool(ICoreTool[GetWorkContextInput, GetWorkContextOutput]):
    """Tool to aggregate work context from Git and GitHub."""

    output_model: ClassVar[type[BaseModel]] = GetWorkContextOutput

    @property
    def name(self) -> str:
        return "get_work_context"

    @property
    def description(self) -> str:
        return (
            "Aggregates context from GitHub Issues, current branch, and workflow phase "
            "to understand what to work on next. Uses deterministic phase detection."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return GetWorkContextInput

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    def __init__(
        self,
        settings: Settings,
        git_manager: GitManager,
        project_manager: ProjectManager,
        state_engine: PhaseStateEngine,
        github_manager: GitHubManager | None = None,
        workphases_config: WorkphasesConfig | None = None,
        *,
        workflow_status_resolver: WorkflowStatusResolver,
        contracts_config: ContractsConfig | None = None,
        context_loaded_writer: IContextLoadedWriter | None = None,
    ) -> None:
        self._settings = settings
        self._git_manager = git_manager
        self._project_manager = project_manager
        self._state_engine = state_engine
        self._github_manager = github_manager
        self._workphases_config = workphases_config
        self._workflow_status_resolver = workflow_status_resolver
        self._contracts_config = contracts_config
        self._context_loaded_writer = context_loaded_writer

    async def execute(
        self,
        params: GetWorkContextInput,
        context: NoteContext,  # noqa: ANN401, ARG002
    ) -> GetWorkContextOutput:
        """Execute work context aggregation."""
        _ = params  # GetWorkContextInput has no fields after C1 (issue #268)

        branch = self._git_manager.get_current_branch()

        workflow_name = ""
        phase = ""
        issue_number = None
        parent_branch = None
        current_cycle = None
        sub_phase = None
        phase_source = "unknown"
        phase_confidence = "unknown"
        invalid_phase_warning = None

        try:
            state = self._state_engine.get_state(branch)
            workflow_name = state.workflow_name if isinstance(state.workflow_name, str) else ""
            phase = state.current_phase if isinstance(state.current_phase, str) else ""

            if isinstance(state.issue_number, int) and not isinstance(state.issue_number, bool):
                issue_number = state.issue_number
            if isinstance(state.parent_branch, str):
                parent_branch = state.parent_branch
            if isinstance(state.current_sub_phase, str):
                sub_phase = state.current_sub_phase

            if (
                self._contracts_config is not None
                and workflow_name
                and phase
                and isinstance(state.current_cycle, int)
                and not isinstance(state.current_cycle, bool)
            ):
                workflow_entry = self._contracts_config.workflows.get(workflow_name)
                if workflow_entry is not None:
                    try:
                        if workflow_entry.get_phase(phase).cycle_based:
                            current_cycle = state.current_cycle
                    except ValueError:
                        pass
            phase_source = "state.json"
            phase_confidence = "high"
        except (StateNotFoundError, FileNotFoundError, OSError, KeyError):
            # uninitialized branch: state.json absent or branch not yet initialized
            pass

        instructions = None
        if self._contracts_config is not None and workflow_name and phase:
            workflow_entry = self._contracts_config.workflows.get(workflow_name)
            if workflow_entry is not None:
                try:
                    instructions = workflow_entry.get_phase(phase).instructions
                except ValueError:
                    invalid_phase_warning = self._build_invalid_phase_warning(
                        workflow=workflow_name,
                        phase=phase,
                        valid_phases=workflow_entry.get_phase_names(),
                    )

        sub_role_hint = instructions.sub_role if instructions is not None else ""
        phase_instructions = ""
        if instructions is not None:
            phase_instructions = instructions.phase_instructions
        elif invalid_phase_warning:
            phase_instructions = (
                "(No phase instructions available until the branch is moved to a valid phase.)"
            )
        else:
            phase_instructions = (
                f"(No instructions defined for workflow: {workflow_name or 'unknown'}, "
                f"phase: {phase or 'unknown'})"
            )

        handover_template = instructions.handover_template if instructions is not None else None

        if self._context_loaded_writer is not None:
            self._context_loaded_writer.set_context_loaded(branch, value=True)

        return GetWorkContextOutput(
            success=True,
            current_branch=branch,
            workflow_name=workflow_name,
            phase=phase,
            issue_number=issue_number,
            parent_branch=parent_branch,
            current_cycle=current_cycle,
            sub_phase=sub_phase,
            phase_source=phase_source,
            phase_confidence=phase_confidence,
            sub_role_hint=sub_role_hint,
            phase_instructions=phase_instructions,
            handover_template=handover_template,
            invalid_phase_warning=invalid_phase_warning,
        )

    def _build_invalid_phase_warning(
        self,
        *,
        workflow: str,
        phase: str,
        valid_phases: list[str],
    ) -> str:
        """Build recovery-oriented warning text for known workflow + invalid phase state."""
        valid_phase_text = ", ".join(valid_phases) if valid_phases else "(none)"
        return (
            f"Invalid workflow state: workflow '{workflow}' does not contains phase '{phase}'.\n"
            f"Valid phases: {valid_phase_text}\n"
            "Recovery: use force_phase_transition to move this branch to a valid phase, "
            "then call get_work_context again."
        )
