# tests/mcp_server/unit/schemas/test_structured_tool_output_migration.py
# template=unit_test version=8825c0bb created=2026-08-22T00:00Z updated=2026-08-22
"""Approved structured DTO clean-break contract tests.

@layer: Tests (Unit)
@dependencies: [pydantic, validation.base, tool_outputs]
@responsibilities:
    - Verify canonical frozen validation-record serialization
    - Verify structured workflow state and numeric pytest duration
    - Verify obsolete presentation fields have no compatibility aliases
"""

import pytest
from pydantic import ValidationError

from mcp_server.schemas.tool_outputs import (
    AutoFixOutput,
    GetWorkContextOutput,
    LabelOperationOutput,
    PhaseTransitionOutput,
    RunTestsOutput,
    SafeEditOutput,
    ScaffoldArtifactOutput,
    WorkflowStateStatus,
)
from mcp_server.validation.base import ValidationIssue


class TestStructuredToolOutputMigration:
    """Clean-break DTO contracts."""

    def test_validation_issue_is_frozen_serializable_and_reused_by_safe_edit(
        self,
    ) -> None:
        issue = ValidationIssue(
            message="Invalid syntax",
            severity="error",
            line=4,
            column=7,
            code="E001",
        )

        output = SafeEditOutput(
            path="example.py",
            passed=False,
            issues=(issue,),
            mode="strict",
            written=False,
        )

        assert output.issues[0] is issue
        assert output.model_dump(mode="json")["issues"] == [
            {
                "message": "Invalid syntax",
                "line": 4,
                "column": 7,
                "code": "E001",
                "severity": "error",
            }
        ]
        with pytest.raises(ValidationError):
            issue.message = "changed"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "status",
        list(WorkflowStateStatus),
    )
    def test_work_context_exposes_structured_workflow_state(
        self,
        status: WorkflowStateStatus,
    ) -> None:
        output = GetWorkContextOutput(
            current_branch="feature/456-example",
            workflow_name="feature",
            phase="research",
            phase_source="state.json",
            phase_confidence="high",
            sub_role_hint="researcher",
            phase_instructions="inspect",
            workflow_state_status=status,
            valid_phases=("research", "design"),
        )

        assert output.workflow_state_status is status
        assert output.valid_phases == ("research", "design")

    def test_run_tests_uses_numeric_optional_duration(self) -> None:
        output = RunTestsOutput(
            exit_code=0,
            passed_count=3,
            failed_count=0,
            skipped_count=0,
            errors_count=0,
            duration_seconds=0.42,
        )

        assert output.duration_seconds == 0.42
        assert "summary_line" not in type(output).model_fields

    @pytest.mark.parametrize(
        ("model", "removed_fields"),
        [
            (AutoFixOutput, {"formatted_modified_files"}),
            (GetWorkContextOutput, {"invalid_phase_warning"}),
            (LabelOperationOutput, {"formatted_labels"}),
            (
                PhaseTransitionOutput,
                {"skipped_gates_warning", "passing_gates_info"},
            ),
            (
                ScaffoldArtifactOutput,
                {
                    "formatted_files_created",
                    "schema_info",
                },
            ),
        ],
    )
    def test_obsolete_presentation_fields_are_absent(
        self,
        model: type[object],
        removed_fields: set[str],
    ) -> None:
        assert removed_fields.isdisjoint(model.model_fields)  # type: ignore[attr-defined]
