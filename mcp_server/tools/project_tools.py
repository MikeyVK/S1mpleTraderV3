"""Project management tools for MCP server.

Phase 0.5: Project initialization with workflow selection.
Issue #39: Atomic initialization of projects.json + state.json.
Issue #79: Parent branch tracking with auto-detection.
Issue #229 Cycle 4: SavePlanningDeliverablesTool with Layer 2 validates schema validation.
"""
import contextlib
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import anyio
from pydantic import BaseModel, Field

from mcp_server.config.workflows import WorkflowConfig
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

logger = logging.getLogger(__name__)


class InitializeProjectInput(BaseModel):
    """Input for initialize_project tool."""

    issue_number: int = Field(..., description="GitHub issue number")
    issue_title: str = Field(..., description="Issue title")
    workflow_name: str = Field(
        ...,
        description=(
            "Workflow from workflows.yaml: feature (7 phases), bug (6), docs (4), "
            "refactor (5), hotfix (3), or custom"
        )
    )
    parent_branch: str | None = Field(
        default=None,
        description=(
            "Parent branch this feature/bug branches from. "
            "If not provided, attempts auto-detection from git reflog. "
            "Example: 'epic/76-quality-gates-tooling'"
        )
    )
    custom_phases: tuple[str, ...] | None = Field(
        default=None,
        description="Custom phase list (required if workflow_name=custom)"
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for custom phases"
    )


class InitializeProjectTool(BaseTool):
    """Tool for initializing projects with atomic state management.

    Phase 0.5: Human selects workflow_name → generates project phase plan.
    Issue #39 Mode 1: Atomic initialization of projects.json + state.json.
    """

    name = "initialize_project"
    description = (
        "Initialize project with phase plan selection. "
        "Human selects workflow_name (feature/bug/docs/refactor/hotfix/custom) "
        "to generate project-specific phase plan."
    )
    args_model = InitializeProjectInput

    def __init__(self, workspace_root: Path | str) -> None:
        """Initialize tool with atomic state management.

        Args:
            workspace_root: Path to workspace root directory
        """
        super().__init__()
        self.workspace_root = Path(workspace_root)
        self.manager = ProjectManager(workspace_root=workspace_root)
        self.git_manager = GitManager()
        self.state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=self.manager
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return InitializeProjectInput.model_json_schema()

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

    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        """Execute project initialization with atomic state creation.

        Issue #39: Creates both projects.json AND state.json atomically.
        Issue #79: Auto-detects parent_branch if not provided.

        Args:
            params: InitializeProjectInput with issue details

        Returns:
            ToolResult with success message and project details

        Raises:
            ValueError: If workflow_name invalid or custom_phases missing
        """
        try:
            start = time.perf_counter()

            # Step 0: Get current branch once and reuse
            branch_start = time.perf_counter()
            with anyio.fail_after(5):
                branch = await anyio.to_thread.run_sync(self.git_manager.get_current_branch)
            logger.debug(
                "initialize_project: got branch in %.1fms",
                (time.perf_counter() - branch_start) * 1000.0,
            )

            # Step 1: Determine parent_branch
            parent_branch = params.parent_branch

            if parent_branch is None:
                # Auto-detect from git reflog
                parent_start = time.perf_counter()
                parent_branch = await self._detect_parent_branch_from_reflog(branch)
                logger.debug(
                    "initialize_project: reflog parent detection in %.1fms",
                    (time.perf_counter() - parent_start) * 1000.0,
                )

                if parent_branch:
                    logger.info(
                        "Auto-detected parent_branch: %s for %s",
                        parent_branch, branch
                    )

            # Step 2: Create projects.json (workflow definition)
            options = None
            if params.custom_phases or params.skip_reason or parent_branch:
                options = ProjectInitOptions(
                    custom_phases=params.custom_phases,
                    skip_reason=params.skip_reason,
                    parent_branch=parent_branch
                )

            init_start = time.perf_counter()
            with anyio.fail_after(20):
                result = await anyio.to_thread.run_sync(
                    lambda: self.manager.initialize_project(
                        issue_number=params.issue_number,
                        issue_title=params.issue_title,
                        workflow_name=params.workflow_name,
                        options=options,
                    )
                )
            logger.debug(
                "initialize_project: initialize_project() in %.1fms",
                (time.perf_counter() - init_start) * 1000.0,
            )

            # Step 3: Determine first phase from workflow
            first_phase = result["required_phases"][0]

            # Step 5: Initialize branch state atomically
            state_start = time.perf_counter()
            with anyio.fail_after(10):
                await anyio.to_thread.run_sync(
                    lambda: self.state_engine.initialize_branch(
                        branch=branch,
                        issue_number=params.issue_number,
                        initial_phase=first_phase,
                    )
                )
            logger.debug(
                "initialize_project: initialize_branch() in %.1fms (total %.1fms)",
                (time.perf_counter() - state_start) * 1000.0,
                (time.perf_counter() - start) * 1000.0,
            )

            # Step 6: Build success message
            success_message = {
                "success": True,
                "issue_number": params.issue_number,
                "workflow_name": params.workflow_name,
                "branch": branch,
                "initial_phase": first_phase,
                "parent_branch": parent_branch,
                "required_phases": result["required_phases"],
                "execution_mode": result["execution_mode"],
                "files_created": [
                    ".st3/projects.json (workflow definition)",
                    ".st3/state.json (branch state)"
                ]
            }

            # Add template info if not custom
            if params.workflow_name != "custom":
                workflow = WorkflowConfig.load().get_workflow(params.workflow_name)
                success_message["description"] = workflow.description

            return ToolResult.text(json.dumps(success_message, indent=2))

        except (ValueError, OSError, RuntimeError) as e:
            return ToolResult.error(str(e))


class GetProjectPlanInput(BaseModel):
    """Input for get_project_plan tool."""

    issue_number: int = Field(..., description="GitHub issue number")


class GetProjectPlanTool(BaseTool):
    """Tool for retrieving project plan."""

    name = "get_project_plan"
    description = "Get project phase plan for issue number"
    args_model = GetProjectPlanInput

    def __init__(self, workspace_root: Path | str) -> None:
        """Initialize tool.

        Args:
            workspace_root: Path to workspace root directory
        """
        super().__init__()
        self.manager = ProjectManager(workspace_root=workspace_root)

    @property
    def input_schema(self) -> dict[str, Any]:
        return GetProjectPlanInput.model_json_schema()

    async def execute(self, params: GetProjectPlanInput) -> ToolResult:
        """Execute project plan retrieval.

        Args:
            params: GetProjectPlanInput with issue_number

        Returns:
            ToolResult with project plan or error
        """
        try:
            plan = self.manager.get_project_plan(issue_number=params.issue_number)
            if plan:
                return ToolResult.text(json.dumps(plan, indent=2))
            return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
        except (ValueError, OSError) as e:
            return ToolResult.error(str(e))


# ---------------------------------------------------------------------------
# Layer 2 validates-entry schema validation
# ---------------------------------------------------------------------------

#: Valid check types and the fields each requires (beyond 'type').
_VALIDATES_REQUIRED_FIELDS: dict[str, list[str]] = {
    "file_exists": ["file"],
    "file_glob": ["file"],
    "contains_text": ["file", "text"],
    "absent_text": ["file", "text"],
    "key_path": ["file", "path"],
}


def validate_spec(deliverable_id: str, validates: dict[str, Any]) -> str | None:
    """Check one *validates* entry for schema correctness.

    Returns an error string when the entry is invalid, else ``None``.

    Args:
        deliverable_id: Deliverable ID for error context (e.g. "D1.1").
        validates: The ``validates`` sub-dict from a deliverable entry.
    """
    check_type = validates.get("type", "")
    if check_type not in _VALIDATES_REQUIRED_FIELDS:
        valid_summary = ", ".join(
            f"{t} (requires: {', '.join(fields)})" for t, fields in _VALIDATES_REQUIRED_FIELDS.items()
        )
        return (
            f"[{deliverable_id}] Unknown validates type '{check_type}'. "
            f"Valid types: {valid_summary}"
        )
    for field in _VALIDATES_REQUIRED_FIELDS[check_type]:
        if field not in validates:
            required = ", ".join(_VALIDATES_REQUIRED_FIELDS[check_type])
            return (
                f"[{deliverable_id}] validates type '{check_type}' requires field '{field}'. "
                f"Required fields: {required}"
            )
    return None


class SavePlanningDeliverablesInput(BaseModel):
    """Input for save_planning_deliverables tool."""

    issue_number: int = Field(..., description="GitHub issue number")
    planning_deliverables: dict[str, Any] = Field(
        ...,
        description=(
            "Planning deliverables dict with tdd_cycles.total + cycles[]. "
            "Each deliverable entry may include a 'validates' spec with type + required fields."
        ),
    )


class SavePlanningDeliverablesTool(BaseTool):
    """Tool to persist planning deliverables for an issue to projects.json.

    Issue #229 Cycle 4 — GAP-04 + GAP-06:
    - Layer 1: MCP JSON Schema (Pydantic, automatic)
    - Layer 2: Runtime validation of every ``validates`` entry before writing.
    """

    name = "save_planning_deliverables"
    description = (
        "Save TDD cycle planning deliverables for an issue to projects.json. "
        "Validates each 'validates' entry schema before persisting."
    )
    args_model = SavePlanningDeliverablesInput

    def __init__(self, workspace_root: Path | str) -> None:
        """Initialize tool.

        Args:
            workspace_root: Workspace root used to resolve project data.
        """
        super().__init__()
        self._manager = ProjectManager(workspace_root=workspace_root)

    async def execute(self, params: SavePlanningDeliverablesInput) -> ToolResult:
        """Persist planning deliverables with Layer 2 schema validation.

        Args:
            params: issue_number + planning_deliverables payload.

        Returns:
            ToolResult success or structured error.
        """
        # Layer 2: validate every validates entry before touching disk
        tdd_cycles = params.planning_deliverables.get("tdd_cycles", {})
        for cycle in tdd_cycles.get("cycles", []):
            for deliverable in cycle.get("deliverables", []):
                if not isinstance(deliverable, dict):
                    continue
                validates = deliverable.get("validates")
                if validates is None:
                    continue
                d_id = deliverable.get("id", "?")
                error = validate_spec(d_id, validates)
                if error:
                    return ToolResult.error(error)

        try:
            self._manager.save_planning_deliverables(
                issue_number=params.issue_number,
                planning_deliverables=params.planning_deliverables,
            )
            return ToolResult.text(
                f"✅ Planning deliverables saved for issue #{params.issue_number}"
            )
        except ValueError as e:
            return ToolResult.error(str(e))
