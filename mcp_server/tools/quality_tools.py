"""Quality tools."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.qa_manager import QAManager
from mcp_server.managers.quality_state_repository import QualityStateMutationConflictError
from mcp_server.schemas.tool_outputs import (
    AutoFixOutput,
    GateFindingDTO,
    GateResultDTO,
    RunQualityGatesOutput,
)
from mcp_server.utils.schema_utils import resolve_schema_refs


class RunQualityGatesInput(BaseModel):
    """Input for RunQualityGatesTool."""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["auto", "branch", "project", "files"] = Field(
        default="auto",
        description=(
            "Scope of the quality gate run. "
            "'auto' = union of changed files and previously failed files; "
            "'branch' = files changed on this branch vs parent; "
            "'project' = all files matching project_scope.include_globs; "
            "'files' = explicit list supplied via the 'files' field."
        ),
    )
    files: list[str] | None = Field(
        default=None,
        description=(
            "Explicit list of files to check. "
            "Required (and non-empty) when scope='files'. "
            "Must be omitted (or null) for all other scope values."
        ),
    )
    verbose: bool = Field(
        default=False,
        description="Whether to capture and cache detailed tracebacks/logs of failing gates.",
    )

    @model_validator(mode="after")
    def _validate_files_scope_contract(self) -> "RunQualityGatesInput":
        """Enforce the two-rule validator contract (design.md §4.6a).

        Rule 1 – files required:  scope='files' and files is None or []  → ValidationError
        Rule 2 – files forbidden: scope != 'files' and files is not None → ValidationError
        """
        if self.scope == "files":
            if not self.files:
                raise ValueError("files must be a non-empty list when scope='files'")
        else:
            if self.files is not None:
                raise ValueError(
                    f"files must be omitted when scope='{self.scope}' "
                    "(only allowed with scope='files')"
                )
        return self


class RunQualityGatesTool(ICoreTool[RunQualityGatesInput, RunQualityGatesOutput]):
    """Tool to run quality gates."""

    @property
    def name(self) -> str:
        return "run_quality_gates"

    @property
    def description(self) -> str:
        return (
            "Run quality gates. "
            "scope='auto' (default): union of changed + previously failed files; "
            "scope='branch': files changed on this branch; "
            "scope='project': all project files; "
            "scope='files': explicit file list supplied via the 'files' field."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return RunQualityGatesInput

    @staticmethod
    def _effective_scope(params: RunQualityGatesInput) -> str:
        """Return authoritative scope value for the current tool execution."""
        return params.scope

    def __init__(self, manager: QAManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        """Get input schema for the tool."""
        if self.args_model is None:
            return {}
        return resolve_schema_refs(self.args_model.model_json_schema())

    async def execute(
        self, params: RunQualityGatesInput, context: NoteContext
    ) -> RunQualityGatesOutput:
        """Execute quality gates and return contract-compliant response DTO."""
        effective_scope = self._effective_scope(params)
        resolved_files = self.manager.resolve_scope(effective_scope, files=params.files)

        kwargs = {}
        if params.verbose:
            kwargs["verbose"] = True

        try:
            result = self.manager.run_quality_gates(
                resolved_files,
                effective_scope=effective_scope,
                **kwargs,
            )
        except QualityStateMutationConflictError as e:
            context.produce(
                Note(key="transition_conflict_recovery", params={"recovery_steps": e.recovery})
            )
            return RunQualityGatesOutput(
                success=False,
                error_message=e.diagnostic,
                overall_pass=False,
                scope=effective_scope,
                file_count=len(resolved_files),
                gates=[],
            )
        except OSError as e:
            context.produce(
                Note(
                    key="quality_state_write_failed_recovery",
                    params={"error_details": str(e)},
                )
            )
            return RunQualityGatesOutput(
                success=False,
                error_message=str(e),
                overall_pass=False,
                scope=effective_scope,
                file_count=len(resolved_files),
                gates=[],
            )

        if not result.get("overall_pass", False) and not params.verbose:
            scope_part = f"scope={params.scope!r}"
            if params.files:
                scope_part += f", files={params.files!r}"
            context.produce(
                Note(
                    key="quality_gates_failed_verbose_suggestion",
                    params={"scope_part": scope_part},
                )
            )

        gates_list = []
        for g in result.get("gates", []):
            gate_name = g.get("name") or g.get("id") or ""
            findings = [
                GateFindingDTO(
                    gate=gate_name,
                    message=issue["message"],
                    file=issue.get("file") or None,
                    line=issue.get("line"),
                    column=issue.get("col"),
                    code=issue.get("rule"),
                    severity=issue.get("severity"),
                    fixable=issue.get("fixable", False),
                    details=issue.get("details"),
                )
                for issue in g.get("issues", [])
            ]
            gates_list.append(
                GateResultDTO(
                    name=gate_name,
                    passed=g.get("passed", False),
                    status=g.get("status") or "",
                    score=str(g.get("score")) if g.get("score") is not None else None,
                    details=g.get("details", ""),
                    findings=findings,
                )
            )

        return RunQualityGatesOutput(
            success=True,
            overall_pass=result.get("overall_pass", False),
            scope=effective_scope,
            file_count=len(resolved_files),
            gates=gates_list,
        )


class AutoFixInput(BaseModel):
    """Input for AutoFixTool."""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["auto", "branch", "project", "files"] = Field(
        default="auto",
        description=(
            "Scope of the auto fix run. "
            "'auto' = union of changed files and previously failed files; "
            "'branch' = files changed on this branch vs parent; "
            "'project' = all files matching project_scope.include_globs; "
            "'files' = explicit list supplied via the 'files' field."
        ),
    )
    files: list[str] | None = Field(
        default=None,
        description=(
            "Explicit list of files to check. "
            "Required (and non-empty) when scope='files'. "
            "Must be omitted (or null) for all other scope values."
        ),
    )

    @model_validator(mode="after")
    def _validate_files_scope_contract(self) -> "AutoFixInput":
        if self.scope == "files":
            if not self.files:
                raise ValueError("files must be a non-empty list when scope='files'")
        else:
            if self.files is not None:
                raise ValueError(
                    f"files must be omitted when scope='{self.scope}' "
                    "(only allowed with scope='files')"
                )
        return self


class AutoFixTool(ICoreTool[AutoFixInput, AutoFixOutput]):
    """Tool to run auto fixes."""

    @property
    def name(self) -> str:
        return "auto_fix"

    @property
    def description(self) -> str:
        return (
            "Execute configured fixer commands on matching files. "
            "scope='auto' (default): union of changed + failed files; "
            "scope='branch': files changed on this branch; "
            "scope='project': all project files; "
            "scope='files': explicit file list supplied via the 'files' field."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return AutoFixInput

    def __init__(self, qa_manager: QAManager) -> None:
        self.qa_manager = qa_manager

    async def execute(self, params: AutoFixInput, context: NoteContext) -> AutoFixOutput:
        """Execute the auto fixes."""
        _ = context
        return self.qa_manager.run_auto_fix(scope=params.scope, files=params.files)
