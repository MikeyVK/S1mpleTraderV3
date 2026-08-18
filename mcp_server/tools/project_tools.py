"""Project management tools for MCP server.

Phase 0.5: Project initialization with workflow selection.
Issue #39: Atomic initialization of deliverables.json + state.json.
Issue #79: Parent branch tracking with auto-detection.
Issue #229 Cycle 4: SavePlanningDeliverablesTool with Layer 2 validates schema validation.
"""

import contextlib
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, ClassVar

import anyio
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager
from mcp_server.schemas import ContractsConfig
from mcp_server.schemas.deliverables import CyclePlanningModel, UpdatePlanningModel
from mcp_server.schemas.tool_outputs import (
    InitializeProjectOutput,
    PhaseDTO,
    PlannedCycleSummary,
    PlanningDeliverablesOutput,
    ProjectPlanOutput,
)
from mcp_server.utils.schema_utils import resolve_schema_refs

logger = logging.getLogger(__name__)


class InitializeProjectInput(BaseModel):
    """Input for initialize_project tool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="GitHub issue number")
    issue_title: str = Field(..., description="Issue title")
    workflow_name: str = Field(
        ...,
        description="Workflow name; valid values are injected from contracts.yaml",
    )
    parent_branch: str | None = Field(
        default=None,
        description=(
            "Parent branch this feature/bug branches from. "
            "If not provided, attempts auto-detection from git reflog. "
            "Example: 'epic/76-quality-gates-tooling'"
        ),
    )
    custom_phases: tuple[str, ...] | None = Field(
        default=None,
        description="Optional phase sequence override for the selected configured workflow",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Required justification when custom_phases overrides the configured sequence",
    )


class InitializeProjectTool(ICoreTool[InitializeProjectInput, InitializeProjectOutput]):
    """Tool for initializing projects with atomic state management.

    Phase 0.5: Human selects workflow_name → generates project phase plan.
    Issue #39 Mode 1: Atomic initialization of deliverables.json + state.json.
    """

    output_model: ClassVar[type[BaseModel]] = InitializeProjectOutput

    @property
    def name(self) -> str:
        return "initialize_project"

    @property
    def description(self) -> str:
        return (
            "Initialize a project with a configured workflow and optional justified "
            "phase-sequence override."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return InitializeProjectInput

    def __init__(
        self,
        workspace_root: Path | str,
        manager: ProjectManager,
        git_manager: GitManager,
        state_engine: PhaseStateEngine,
        contracts_config: ContractsConfig | None = None,
    ) -> None:
        """Initialize tool with injected project dependencies."""
        self.workspace_root = Path(workspace_root)
        self.manager = manager
        self.git_manager = git_manager
        self.state_engine = state_engine
        self._contracts_config = contracts_config

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model is None:
            return {}
        schema = resolve_schema_refs(self.args_model.model_json_schema())
        if self._contracts_config is not None:
            schema["properties"]["workflow_name"]["enum"] = list(
                self._contracts_config.workflows.keys()
            )
        return schema

    def _detect_parent_branch_from_reflog_sync(self, current_branch: str) -> str | None:
        """Detect parent branch from git reflog.

        This is intentionally synchronous and must run in a worker thread. On Windows
        we've observed that long-running git subprocesses can make MCP (stdio) look
        "hung"; doing the subprocess work in a thread plus using robust kill logic
        keeps the server responsive.

        To keep reconciliation accurate without producing huge output, we read only
        the reflog *subject* lines via `--pretty=%gs`.
        """
        max_entries = 5000
        timeout_s = 5.0

        cmd = [
            "git",
            "--no-pager",
            "reflog",
            "show",
            "--all",
            "-n",
            str(max_entries),
            "--pretty=%gs",
        ]

        def kill_tree(pid: int) -> None:
            if os.name == "nt":
                # Kill the entire tree so `git` doesn't linger.
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2,
                )
                return
            try:
                os.kill(pid, 9)
            except OSError:
                return

        try:
            with subprocess.Popen(
                cmd,
                cwd=str(self.workspace_root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            ) as proc:
                try:
                    stdout, _stderr = proc.communicate(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    kill_tree(proc.pid)
                    with contextlib.suppress(OSError, subprocess.TimeoutExpired, ValueError):
                        proc.communicate(timeout=1)
                    logger.warning(
                        "Git reflog failed: Command timed out after %ss",
                        timeout_s,
                    )
                    return None

                if proc.returncode:
                    logger.warning("Git reflog failed (exit %s)", proc.returncode)
                    return None

            pattern = f"checkout: moving from (.+?) to {re.escape(current_branch)}"
            for line in stdout.splitlines():
                match = re.search(pattern, line)
                if match:
                    parent = match.group(1)
                    logger.info("Detected parent branch from reflog: %s", parent)
                    return parent

            logger.warning("No parent branch found in reflog for %s", current_branch)
            return None

        except (OSError, ValueError) as e:
            logger.warning("Git reflog failed: %s", e)
            return None

    async def _detect_parent_branch_from_reflog(self, current_branch: str) -> str | None:
        return await anyio.to_thread.run_sync(
            lambda: self._detect_parent_branch_from_reflog_sync(current_branch),
            cancellable=True,
        )

    async def execute(
        self,
        params: InitializeProjectInput,
        context: NoteContext,  # noqa: ANN401, ARG002
    ) -> InitializeProjectOutput:
        """Execute project initialization with atomic state creation.

        Issue #39: Creates both deliverables.json AND state.json atomically.
        Issue #79: Auto-detects parent_branch if not provided.

        Args:
            params: InitializeProjectInput with issue details

        Returns:
            InitializeProjectOutput
        """
        try:
            # Step 0: Get current branch once and reuse
            with anyio.fail_after(5):
                branch = await anyio.to_thread.run_sync(self.git_manager.get_current_branch)

            # Step 1: Determine parent_branch
            parent_branch = params.parent_branch

            if parent_branch is None:
                # Auto-detect from git reflog
                parent_branch = await self._detect_parent_branch_from_reflog(branch)
                if parent_branch:
                    logger.info("Auto-detected parent_branch: %s for %s", parent_branch, branch)

            # Step 2: Create deliverables.json (workflow definition)
            options = None
            if params.custom_phases or params.skip_reason or parent_branch:
                options = ProjectInitOptions(
                    custom_phases=params.custom_phases,
                    skip_reason=params.skip_reason,
                    parent_branch=parent_branch,
                )

            with anyio.fail_after(20):
                result = await anyio.to_thread.run_sync(
                    lambda: self.manager.initialize_project(
                        issue_number=params.issue_number,
                        issue_title=params.issue_title,
                        workflow_name=params.workflow_name,
                        options=options,
                    )
                )

            # Step 3: Determine first phase from workflow
            first_phase = result["required_phases"][0]

            # Step 5: Initialize branch state atomically
            with anyio.fail_after(10):
                await anyio.to_thread.run_sync(
                    lambda: self.state_engine.initialize_branch(
                        branch=branch,
                        issue_number=params.issue_number,
                        initial_phase=first_phase,
                    )
                )

            return InitializeProjectOutput(
                success=True,
                issue_number=params.issue_number,
                workflow_name=params.workflow_name,
                branch=branch,
                initial_phase=first_phase,
                parent_branch=parent_branch,
                required_phases=result["required_phases"],
                execution_mode=result["execution_mode"],
                files_created=[
                    "deliverables.json (workflow definition)",
                    "state.json (branch state)",
                ],
            )

        except Exception as e:
            return InitializeProjectOutput(
                success=False,
                error_message=str(e),
                issue_number=params.issue_number,
                workflow_name=params.workflow_name,
                branch="",
                initial_phase="",
                execution_mode="",
            )


class GetProjectPlanInput(BaseModel):
    """Input for get_project_plan tool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="GitHub issue number")


class GetProjectPlanTool(ICoreTool[GetProjectPlanInput, ProjectPlanOutput]):
    """Tool for retrieving project plan."""

    output_model: ClassVar[type[BaseModel]] = ProjectPlanOutput

    @property
    def name(self) -> str:
        return "get_project_plan"

    @property
    def description(self) -> str:
        return "Get project phase plan for issue number"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return GetProjectPlanInput

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model is None:
            return {}
        return resolve_schema_refs(self.args_model.model_json_schema())

    def __init__(self, manager: ProjectManager) -> None:
        """Initialize tool with injected ProjectManager."""
        self.manager = manager

    async def execute(
        self,
        params: GetProjectPlanInput,
        context: NoteContext,  # noqa: ANN401
    ) -> ProjectPlanOutput:
        """Execute project plan retrieval.

        Args:
            params: GetProjectPlanInput with issue_number
            context: Call context
        """
        try:
            plan = self.manager.get_project_plan(issue_number=params.issue_number)
            if plan:
                required_phases = plan.get("required_phases", [])
                current_phase = plan.get("current_phase", "")
                curr_phase_name = current_phase.split(":")[0] if current_phase else ""

                phases_list = []
                current_found = False
                for p_name in required_phases:
                    if p_name == curr_phase_name:
                        status = "active"
                        current_found = True
                    elif current_found:
                        status = "pending"
                    else:
                        status = "completed" if curr_phase_name else "pending"
                    phases_list.append(PhaseDTO(name=p_name, status=status, tasks=[]))

                return ProjectPlanOutput(
                    success=True,
                    issue_number=params.issue_number,
                    workflow_name=plan.get("workflow_name", ""),
                    phases=phases_list,
                )

            context.produce(
                Note(
                    key="initialize_project_suggestion",
                    params={
                        "issue_number": params.issue_number,
                    },
                )
            )
            return ProjectPlanOutput(
                success=False,
                error_message=f"No project plan found for issue #{params.issue_number}",
                issue_number=params.issue_number,
                workflow_name="",
                phases=[],
            )
        except (ValueError, OSError) as e:
            return ProjectPlanOutput(
                success=False,
                error_message=str(e),
                issue_number=params.issue_number,
                workflow_name="",
                phases=[],
            )


# ---------------------------------------------------------------------------
# Planning deliverables tools
# ---------------------------------------------------------------------------


class SavePlanningDeliverablesInput(BaseModel):
    """Input for save_planning_deliverables tool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="GitHub issue number")
    planning_deliverables: CyclePlanningModel = Field(
        ...,
        description=(
            "Planning deliverables with cycles.total + cycles[]. "
            "Each deliverable entry may include a 'validates' spec with type + required fields."
        ),
    )


class SavePlanningDeliverablesTool(
    ICoreTool[SavePlanningDeliverablesInput, PlanningDeliverablesOutput]
):
    """Tool to persist planning deliverables for an issue to deliverables.json.

    Issue #229 Cycle 4 / Issue #390:
    - Layer 1: MCP JSON Schema (Pydantic, automatic)
    - Defer schema validation entirely to CyclePlanningModel.
    """

    output_model: ClassVar[type[BaseModel]] = PlanningDeliverablesOutput

    @property
    def name(self) -> str:
        return "save_planning_deliverables"

    @property
    def description(self) -> str:
        return (
            "Save cycle planning deliverables for an issue to deliverables.json. "
            "Validates the schema before persisting."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return SavePlanningDeliverablesInput

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model is None:
            return {}
        return resolve_schema_refs(self.args_model.model_json_schema())

    def __init__(
        self,
        manager: ProjectManager,
        workspace_root: Path | str | None = None,
    ) -> None:
        """Initialize tool with injected ProjectManager."""
        del workspace_root
        self._manager = manager

    async def execute(
        self, params: SavePlanningDeliverablesInput, context: NoteContext
    ) -> PlanningDeliverablesOutput:
        """Persist planning deliverables.

        Args:
            params: issue_number + planning_deliverables payload.
            context: Call context
        """
        del context
        try:
            pd_dict = params.planning_deliverables.model_dump(exclude_none=True)
            self._manager.save_planning_deliverables(
                issue_number=params.issue_number,
                planning_deliverables=pd_dict,
            )

            # Load project plan to extract the complete planning_deliverables
            plan = self._manager.get_project_plan(issue_number=params.issue_number)
            if not plan or "planning_deliverables" not in plan:
                return PlanningDeliverablesOutput(
                    success=False,
                    error_message="Planning deliverables not found after saving",
                    issue_number=params.issue_number,
                    total_cycles=0,
                    total_deliverables=0,
                    cycles=[],
                )

            pd = plan["planning_deliverables"]
            cycles_data = pd.get("cycles", {}).get("cycles", [])
            cycles_summaries = []
            cycle_deliverables_count = 0
            for c in cycles_data:
                cycle_num = c.get("cycle_number", 0)
                delivs_count = len(c.get("deliverables", []))
                cycle_deliverables_count += delivs_count
                cycles_summaries.append(
                    PlannedCycleSummary(
                        cycle_number=cycle_num,
                        deliverables_count=delivs_count,
                    )
                )

            phase_deliverables_count = 0
            if self._manager.workphases_config is not None:
                phase_keys = list(self._manager.workphases_config.phases.keys())
            else:
                phase_keys = [
                    "research",
                    "planning",
                    "design",
                    "implementation",
                    "validation",
                    "documentation",
                    "ready",
                    "coordination",
                ]
            for pk in phase_keys:
                if pk in pd:
                    phase_deliverables_count += len(pd[pk].get("deliverables", []))

            total_deliverables = cycle_deliverables_count + phase_deliverables_count

            return PlanningDeliverablesOutput(
                success=True,
                issue_number=params.issue_number,
                total_cycles=len(cycles_summaries),
                total_deliverables=total_deliverables,
                cycles=cycles_summaries,
            )
        except Exception as e:
            return PlanningDeliverablesOutput(
                success=False,
                error_message=str(e),
                issue_number=params.issue_number,
                total_cycles=0,
                total_deliverables=0,
                cycles=[],
            )


class UpdatePlanningDeliverablesInput(BaseModel):
    """Input for update_planning_deliverables tool."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., description="GitHub issue number")
    planning_deliverables: UpdatePlanningModel = Field(
        ...,
        description=(
            "Partial or full planning deliverables to merge into the existing entry. "
            "New cycles are appended; existing cycles have deliverables merged by id. "
            "Deliverable entries may include a 'validates' spec with type + required fields."
        ),
    )


class UpdatePlanningDeliverablesTool(
    ICoreTool[UpdatePlanningDeliverablesInput, PlanningDeliverablesOutput]
):
    """Tool to merge-update planning deliverables for an issue in deliverables.json.

    Issue #229 Cycle 5 / Issue #390:
    - Requires save_planning_deliverables to have been called first.
    - Merge strategy: new cycle -> append; existing cycle + new id -> append;
      existing id -> overwrite.
    - Defer schema validation entirely to UpdatePlanningModel.
    """

    output_model: ClassVar[type[BaseModel]] = PlanningDeliverablesOutput

    @property
    def name(self) -> str:
        return "update_planning_deliverables"

    @property
    def description(self) -> str:
        return (
            "Merge-update cycle planning deliverables for an issue in deliverables.json. "
            "Must be preceded by save_planning_deliverables. "
            "New cycles are appended; deliverables within existing cycles are merged by id."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return UpdatePlanningDeliverablesInput

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model is None:
            return {}
        return resolve_schema_refs(self.args_model.model_json_schema())

    def __init__(
        self,
        manager: ProjectManager,
        workspace_root: Path | str | None = None,
    ) -> None:
        """Initialize tool with injected ProjectManager."""
        del workspace_root
        self._manager = manager

    async def execute(
        self, params: UpdatePlanningDeliverablesInput, context: NoteContext
    ) -> PlanningDeliverablesOutput:
        """Merge planning deliverables.

        Args:
            params: issue_number + planning_deliverables payload.
            context: Call context
        """
        del context
        try:
            pd_dict = params.planning_deliverables.model_dump(exclude_none=True)
            self._manager.update_planning_deliverables(
                issue_number=params.issue_number,
                planning_deliverables=pd_dict,
            )

            # Load project plan to extract the complete planning_deliverables
            plan = self._manager.get_project_plan(issue_number=params.issue_number)
            if not plan or "planning_deliverables" not in plan:
                return PlanningDeliverablesOutput(
                    success=False,
                    error_message="Planning deliverables not found after updating",
                    issue_number=params.issue_number,
                    total_cycles=0,
                    total_deliverables=0,
                    cycles=[],
                )

            pd = plan["planning_deliverables"]
            cycles_data = pd.get("cycles", {}).get("cycles", [])
            cycles_summaries = []
            cycle_deliverables_count = 0
            for c in cycles_data:
                cycle_num = c.get("cycle_number", 0)
                delivs_count = len(c.get("deliverables", []))
                cycle_deliverables_count += delivs_count
                cycles_summaries.append(
                    PlannedCycleSummary(
                        cycle_number=cycle_num,
                        deliverables_count=delivs_count,
                    )
                )

            phase_deliverables_count = 0
            if self._manager.workphases_config is not None:
                phase_keys = list(self._manager.workphases_config.phases.keys())
            else:
                phase_keys = [
                    "research",
                    "planning",
                    "design",
                    "implementation",
                    "validation",
                    "documentation",
                    "ready",
                    "coordination",
                ]
            for pk in phase_keys:
                if pk in pd:
                    phase_deliverables_count += len(pd[pk].get("deliverables", []))

            total_deliverables = cycle_deliverables_count + phase_deliverables_count

            return PlanningDeliverablesOutput(
                success=True,
                issue_number=params.issue_number,
                total_cycles=len(cycles_summaries),
                total_deliverables=total_deliverables,
                cycles=cycles_summaries,
            )
        except Exception as e:
            return PlanningDeliverablesOutput(
                success=False,
                error_message=str(e),
                issue_number=params.issue_number,
                total_cycles=0,
                total_deliverables=0,
                cycles=[],
            )
