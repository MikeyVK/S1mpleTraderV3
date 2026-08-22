# tests/unit/mcp_server/tools/test_quality_tools.py
"""Tests for quality tools.

@layer: Tests (Unit)
@dependencies: [pytest, pathlib, mcp_server.tools.quality_tools]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

# Standard library
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

# Third-party
import pytest
from pydantic import ValidationError

# Module under test
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.schemas import tool_outputs
from mcp_server.schemas.tool_outputs import RunQualityGatesOutput
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.test_support import make_qa_manager


def _summary_text(result: ToolResult | RunQualityGatesOutput) -> str:
    """Extract summary text, supporting both ToolResult and RunQualityGatesOutput DTO."""
    if isinstance(result, ToolResult):
        item = result.content[1]
        assert item["type"] == "text", f"Expected content[1] type='text', got '{item['type']}'"
        return item["text"]
    emoji = "✅" if result.overall_pass else "❌"
    return f"{emoji} Quality gates: {result.overall_pass}"


def _compact_payload(result: ToolResult | RunQualityGatesOutput) -> dict[str, Any]:
    """Extract compact JSON payload, supporting both ToolResult and DTO."""
    if isinstance(result, ToolResult):
        item = result.content[0]
        assert item["type"] == "json", f"Expected content[0] type='json', got '{item['type']}'"
        return item["json"]
    return result.model_dump()


class TestRunQualityGatesTool:
    """Tests for RunQualityGatesTool."""

    @pytest.mark.asyncio
    async def test_no_files_triggers_project_level(self) -> None:
        """Test scope='project' resolves to empty list and is forwarded to manager."""
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = []
        mock_manager.run_quality_gates.return_value = {
            "version": "1.0.0",
            "mode": "project-level",
            "files": [],
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 3,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [
                {
                    "name": "Tests",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                }
            ],
            "overall_pass": True,
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(scope="project"), NoteContext())

        text = _summary_text(result)
        assert "Quality gates" in text
        mock_manager.resolve_scope.assert_called_once_with("project", files=None)
        mock_manager.run_quality_gates.assert_called_once_with(
            [],
            effective_scope="project",
        )

    @pytest.mark.asyncio
    async def test_quality_gates_passed(self) -> None:
        """Test clean quality pass returns ✅ summary line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [
                {
                    "name": "pylint",
                    "passed": True,
                    "status": "passed",
                    "score": 10.0,
                    "issues": [],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"]), NoteContext()
        )

        text = _summary_text(result)
        assert "✅" in text

    @pytest.mark.asyncio
    async def test_quality_gates_failed_with_issues(self) -> None:
        """Test failed quality gates returns ❌ summary line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "pylint",
                    "passed": False,
                    "status": "failed",
                    "score": 5.0,
                    "issues": [
                        {
                            "file": "foo.py",
                            "line": 10,
                            "column": 4,
                            "code": "C0111",
                            "message": "Missing docstring",
                        }
                    ],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"]), NoteContext()
        )

        text = _summary_text(result)
        assert "❌" in text

    @pytest.mark.asyncio
    async def test_quality_gates_failed_prints_hints(self) -> None:
        """Test gate with hints — summary line is still returned."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "Gate 3: Line Length",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "issues": [{"message": "E501"}],
                    "hints": ["Re-run: python -m ruff check file.py"],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"]), NoteContext()
        )

        text = _summary_text(result)
        assert "❌" in text
        assert "Quality gates" in text

    @pytest.mark.asyncio
    async def test_quality_gate_finding_missing_message_fails_fast(self) -> None:
        """An invalid manager issue must not receive invented presentation text."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": False,
            "gates": [
                {
                    "name": "check",
                    "passed": False,
                    "status": "failed",
                    "score": 0,
                    "issues": [{}],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)

        with pytest.raises(KeyError, match="message"):
            await tool.execute(
                RunQualityGatesInput(scope="files", files=["foo.py"]),
                NoteContext(),
            )

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_response_is_native_json_object(self) -> None:
        """Tool returns RunQualityGatesOutput DTO."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "version": "1.0.0",
            "mode": "file-specific",
            "files": ["foo.py"],
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [
                {
                    "id": 1,
                    "name": "Gate 0: Ruff Format",
                    "passed": True,
                    "status": "passed",
                    "skip_reason": None,
                    "score": "Pass",
                    "issues": [],
                }
            ],
            "overall_pass": True,
        }
        mock_manager.build_compact_result.return_value = {
            "overall_pass": True,
            "duration_ms": 0,
            "gates": [
                {
                    "id": "Gate 0: Ruff Format",
                    "passed": True,
                    "skipped": False,
                    "status": "passed",
                    "violations": [],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"]), NoteContext()
        )

        assert isinstance(result, RunQualityGatesOutput)
        assert result.overall_pass is True
        assert len(result.gates) == 1
        assert result.gates[0].name == "Gate 0: Ruff Format"

    def test_schema(self) -> None:
        """Test tool schema has files property."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "files" in schema["properties"]


class TestRunQualityGatesInputC28:
    """C28: scope="files" as 4th Literal value with conditional files companion field.

    RED tests — all must fail until C28 GREEN is implemented.
    """

    # --- Validator: files REQUIRED when scope="files" ---

    def test_scope_files_without_files_raises(self) -> None:
        """scope='files' with no files field raises ValidationError (files required)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="files")

    def test_scope_files_with_empty_list_raises(self) -> None:
        """scope='files' with empty list raises ValidationError (empty not allowed)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="files", files=[])

    def test_scope_files_with_files_is_valid(self) -> None:
        """scope='files' with non-empty files is valid."""
        params = RunQualityGatesInput(scope="files", files=["a.py", "b.py"])
        assert params.scope == "files"
        assert params.files == ["a.py", "b.py"]

    # --- Validator: files FORBIDDEN when scope != "files" ---

    def test_scope_auto_with_files_raises(self) -> None:
        """scope='auto' with files supplied raises ValidationError (files forbidden)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="auto", files=["a.py"])

    def test_scope_branch_with_files_raises(self) -> None:
        """scope='branch' with files supplied raises ValidationError (files forbidden)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="branch", files=["a.py"])

    def test_scope_project_with_files_raises(self) -> None:
        """scope='project' with files supplied raises ValidationError (files forbidden)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(scope="project", files=["a.py"])

    # --- Valid non-files scopes ---

    def test_scope_auto_without_files_is_valid(self) -> None:
        """scope='auto' with no files is valid."""
        params = RunQualityGatesInput(scope="auto")
        assert params.scope == "auto"
        assert params.files is None

    def test_scope_branch_without_files_is_valid(self) -> None:
        """scope='branch' with no files is valid."""
        params = RunQualityGatesInput(scope="branch")
        assert params.scope == "branch"

    def test_scope_project_without_files_is_valid(self) -> None:
        """scope='project' with no files is valid."""
        params = RunQualityGatesInput(scope="project")
        assert params.scope == "project"

    # --- Default scope ---

    def test_default_scope_is_auto(self) -> None:
        """Default scope is 'auto' when no scope is provided."""
        params = RunQualityGatesInput()
        assert params.scope == "auto"

    # --- Old bare-files API rejected ---

    def test_bare_files_api_without_scope_rejected(self) -> None:
        """Bare files=[] without scope raises ValidationError (old API no longer valid)."""
        with pytest.raises(ValidationError):
            RunQualityGatesInput(files=[])

    # --- Schema reflects new API ---

    def test_schema_has_scope_not_bare_files(self) -> None:
        """Input schema exposes 'scope' field."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "scope" in schema["properties"]

    # --- execute() routes scope="files" correctly ---

    @pytest.mark.asyncio
    async def test_execute_scope_files_passes_list_to_manager(self) -> None:
        """execute(scope='files', files=[...]) passes the list verbatim to run_quality_gates."""
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["src/foo.py"]
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [],
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(
            RunQualityGatesInput(scope="files", files=["src/foo.py"]), NoteContext()
        )

        mock_manager.run_quality_gates.assert_called_once_with(
            ["src/foo.py"],
            effective_scope="files",
        )
        assert isinstance(result, RunQualityGatesOutput)


class TestRunQualityGatesScopeGuardC41:
    """Cycle 41 RED: non-auto scopes must not mutate auto baseline lifecycle state."""

    @staticmethod
    def _stub_quality_config() -> SimpleNamespace:
        """Return minimal config stub sufficient for QAManager.run_quality_gates()."""
        gate = SimpleNamespace(
            name="Gate 1: Stub",
            scope=None,
            capabilities=SimpleNamespace(file_types=[".py"]),
        )
        return SimpleNamespace(
            active_gates=["gate1_stub"],
            gates={"gate1_stub": gate},
            artifact_logging=SimpleNamespace(
                enabled=False,
                output_dir="temp/qa_logs",
                max_files=10,
            ),
        )

    @pytest.mark.asyncio
    async def test_scope_files_pass_run_does_not_advance_baseline(self) -> None:
        """RED: scope='files' pass run must not call baseline advance path."""
        manager = make_qa_manager(Path.cwd(), quality_config=self._stub_quality_config())
        tool = RunQualityGatesTool(manager=manager)

        with (
            patch.object(manager, "resolve_scope", return_value=["backend/__init__.py"]),
            patch.object(
                manager,
                "execute_gate",
                return_value={
                    "gate_number": 1,
                    "name": "Gate 1: Stub",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                    "duration_ms": 0,
                },
            ),
            patch.object(manager, "_advance_baseline_on_all_pass") as mock_advance,
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_accumulate,
        ):
            await tool.execute(
                RunQualityGatesInput(scope="files", files=["backend/__init__.py"]), NoteContext()
            )

        mock_advance.assert_not_called()
        mock_accumulate.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scope", ["branch", "project"])
    async def test_non_auto_pass_runs_do_not_reset_auto_failed_state(self, scope: str) -> None:
        """RED: scope='branch'/'project' pass runs must not hit auto baseline mutation path."""
        manager = make_qa_manager(Path.cwd(), quality_config=self._stub_quality_config())
        tool = RunQualityGatesTool(manager=manager)

        with (
            patch.object(manager, "resolve_scope", return_value=["backend/__init__.py"]),
            patch.object(
                manager,
                "execute_gate",
                return_value={
                    "gate_number": 1,
                    "name": "Gate 1: Stub",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                    "duration_ms": 0,
                },
            ),
            patch.object(manager, "_advance_baseline_on_all_pass") as mock_advance,
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_accumulate,
        ):
            await tool.execute(RunQualityGatesInput(scope=scope), NoteContext())

        mock_advance.assert_not_called()
        mock_accumulate.assert_not_called()


class TestRunQualityGatesFailedSubsetC42:
    """Cycle 42 RED: auto scope should persist only failing-file subset."""

    @staticmethod
    def _stub_quality_config() -> SimpleNamespace:
        gate = SimpleNamespace(
            name="Gate 1: Stub",
            scope=None,
            capabilities=SimpleNamespace(file_types=[".py"]),
        )
        return SimpleNamespace(
            active_gates=["gate1_stub"],
            gates={"gate1_stub": gate},
            artifact_logging=SimpleNamespace(
                enabled=False,
                output_dir="temp/qa_logs",
                max_files=10,
            ),
        )

    @pytest.mark.asyncio
    async def test_auto_mixed_result_accumulates_only_failing_subset(self) -> None:
        """RED: only failing file(s) should be sent to failed_files accumulator."""
        manager = make_qa_manager(Path.cwd(), quality_config=self._stub_quality_config())
        tool = RunQualityGatesTool(manager=manager)
        resolved_files = ["a.py", "b.py"]

        with (
            patch.object(manager, "resolve_scope", return_value=resolved_files),
            patch("pathlib.Path.exists", return_value=True),
            patch.object(
                manager,
                "execute_gate",
                return_value={
                    "gate_number": 1,
                    "name": "Gate 1: Stub",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "issues": [
                        {
                            "file": "a.py",
                            "line": 1,
                            "col": 1,
                            "rule": "X",
                            "message": "boom",
                        }
                    ],
                    "duration_ms": 0,
                },
            ),
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_accumulate,
            patch.object(manager, "_advance_baseline_on_all_pass") as mock_advance,
        ):
            await tool.execute(RunQualityGatesInput(scope="auto"), NoteContext())

        mock_advance.assert_not_called()
        mock_accumulate.assert_called_once_with(["a.py"])

    @pytest.mark.asyncio
    async def test_auto_mixed_result_must_not_accumulate_full_resolved_set(self) -> None:
        """RED: accumulator input must not equal full evaluated set when only subset fails."""
        manager = make_qa_manager(Path.cwd(), quality_config=self._stub_quality_config())
        tool = RunQualityGatesTool(manager=manager)
        resolved_files = ["a.py", "b.py"]

        with (
            patch.object(manager, "resolve_scope", return_value=resolved_files),
            patch("pathlib.Path.exists", return_value=True),
            patch.object(
                manager,
                "execute_gate",
                return_value={
                    "gate_number": 1,
                    "name": "Gate 1: Stub",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "issues": [{"file": "a.py", "message": "boom"}],
                    "duration_ms": 0,
                },
            ),
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_accumulate,
        ):
            await tool.execute(RunQualityGatesInput(scope="auto"), NoteContext())

        assert mock_accumulate.call_count == 1
        accumulated = mock_accumulate.call_args.args[0]
        assert accumulated != resolved_files


class TestEffectiveScopePropagationC43:
    """Cycle 43: effective scope is explicit and consistent through tool → manager."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("scope", "files_arg", "resolved"),
        [
            ("auto", None, ["a.py"]),
            ("branch", None, ["b.py"]),
            ("project", None, ["c.py"]),
            ("files", ["src/x.py"], ["src/x.py"]),
        ],
    )
    async def test_execute_passes_effective_scope_to_manager(
        self,
        scope: str,
        files_arg: list[str] | None,
        resolved: list[str],
    ) -> None:
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = resolved
        manager_result = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [],
        }
        mock_manager.run_quality_gates.return_value = manager_result
        tool = RunQualityGatesTool(manager=mock_manager)

        params = RunQualityGatesInput(scope=scope, files=files_arg)
        await tool.execute(params, NoteContext())

        mock_manager.resolve_scope.assert_called_once_with(scope, files=files_arg)
        mock_manager.run_quality_gates.assert_called_once_with(
            resolved,
            effective_scope=scope,
        )


class TestScopeSwitchInvariantsC43:
    """Cycle 43: explicit scope propagation remains stable across call sequences."""

    @pytest.mark.asyncio
    async def test_auto_files_auto_sequence_preserves_scope_intent(self) -> None:
        mock_manager = MagicMock()
        mock_manager.resolve_scope.side_effect = [
            ["changed_auto.py"],
            ["target_file.py"],
            ["changed_auto_2.py"],
        ]
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [],
        }
        tool = RunQualityGatesTool(manager=mock_manager)

        await tool.execute(RunQualityGatesInput(scope="auto"), NoteContext())
        await tool.execute(
            RunQualityGatesInput(scope="files", files=["target_file.py"]), NoteContext()
        )
        await tool.execute(RunQualityGatesInput(scope="auto"), NoteContext())

        assert mock_manager.run_quality_gates.call_args_list[0].kwargs["effective_scope"] == "auto"
        assert mock_manager.run_quality_gates.call_args_list[1].kwargs["effective_scope"] == "files"
        assert mock_manager.run_quality_gates.call_args_list[2].kwargs["effective_scope"] == "auto"


class TestRunQualityGatesToolConflictC8:
    """C8: RunQualityGatesTool surfaces quality-state write failures explicitly.

    When a quality-state mutation fails (e.g., OSError from AtomicJsonWriter),
    the tool must return ToolResult.error with an actionable message and emit a
    RecoveryNote through the provided NoteContext.
    """

    @pytest.mark.asyncio
    async def test_run_quality_gates_returns_error_on_os_error(self) -> None:
        """RunQualityGatesTool returns error DTO when manager raises OSError."""
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["some_file.py"]
        mock_manager.run_quality_gates.side_effect = OSError("Quality state write failed")

        tool = RunQualityGatesTool(manager=mock_manager)
        context = NoteContext()
        result = await tool.execute(RunQualityGatesInput(scope="auto"), context)

        assert result.success is False
        assert result.error_message is not None
        assert "Quality state write failed" in result.error_message

    @pytest.mark.asyncio
    async def test_run_quality_gates_emits_recovery_note_on_os_error(self) -> None:
        """RunQualityGatesTool emits RecoveryNote through NoteContext on quality-state failure."""
        from mcp_server.core.operation_notes import Note  # noqa: PLC0415

        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["some_file.py"]
        mock_manager.run_quality_gates.side_effect = OSError("Quality state write failed")

        tool = RunQualityGatesTool(manager=mock_manager)
        context = NoteContext()
        await tool.execute(RunQualityGatesInput(scope="auto"), context)

        notes = [n for n in context.of_type(Note) if n.key == "quality_state_write_failed_recovery"]
        assert len(notes) == 1
        err_details = notes[0].params.get("error_details", "").lower()
        assert "quality" in err_details or "retry" in err_details


# C3 RED — RunQualityGatesTool catches QualityStateMutationConflictError (issue #292)


class TestRunQualityGatesConflictErrorC3:
    """C3 (#292): RunQualityGatesTool must catch QualityStateMutationConflictError.

    When FileQualityStateRepository raises QualityStateMutationConflictError (lock timeout),
    the tool must return ToolResult.error(e.diagnostic) and emit RecoveryNote(message=e.recovery).
    """

    @pytest.mark.asyncio
    async def test_conflict_error_returns_recovery_note_and_error(self) -> None:
        """QualityStateMutationConflictError raised by manager -> RecoveryNote + error (C3-D5/6)."""
        from mcp_server.core.operation_notes import Note  # noqa: PLC0415
        from mcp_server.managers.quality_state_repository import (  # noqa: PLC0415
            QualityStateMutationConflictError,
        )

        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["some_file.py"]
        mock_manager.run_quality_gates.side_effect = QualityStateMutationConflictError(
            diagnostic="Quality state write failed — lock timeout (5s)",
            recovery="Retry the quality-gates run once the current run completes.",
        )

        tool = RunQualityGatesTool(manager=mock_manager)
        context = NoteContext()
        result = await tool.execute(RunQualityGatesInput(scope="auto"), context)

        assert result.success is False, (
            "must return success=False on QualityStateMutationConflictError"
        )
        assert result.error_message is not None
        assert (
            "lock timeout" in result.error_message.lower()
            or "write failed" in result.error_message.lower()
        ), f"diagnostic must appear in error_message, got: {result.error_message!r}"
        notes = [n for n in context.of_type(Note) if n.key == "transition_conflict_recovery"]
        assert len(notes) == 1, f"must emit exactly one Note, got {len(notes)}"
        assert "retry" in notes[0].params.get("recovery_steps", "").lower(), (
            f"recovery hint must mention retry, got: {notes[0].params.get('recovery_steps')!r}"
        )


def test_c5_render_text_output_is_removed() -> None:
    """Verify that _render_text_output has been removed from RunQualityGatesTool."""
    assert not hasattr(RunQualityGatesTool, "_render_text_output")


class TestRunQualityGatesVerboseOption:
    """Cycle 11: run_quality_gates tool verbose option tests."""

    def test_input_schema_accepts_verbose(self) -> None:
        """Verify RunQualityGatesInput accepts verbose field."""
        params = RunQualityGatesInput(scope="auto", verbose=True)
        assert params.verbose is True

        # Test default is False
        params_default = RunQualityGatesInput(scope="auto")
        assert params_default.verbose is False

    @pytest.mark.asyncio
    async def test_verbose_propagated_to_manager(self) -> None:
        """Verify RunQualityGatesTool propagates verbose to QAManager."""
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["foo.py"]
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [
                {
                    "name": "ruff",
                    "passed": True,
                    "status": "passed",
                    "details": "All clean",
                }
            ],
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        context = NoteContext()
        await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"], verbose=True), context
        )
        mock_manager.run_quality_gates.assert_called_once_with(
            ["foo.py"],
            effective_scope="files",
            verbose=True,
        )

    @pytest.mark.asyncio
    async def test_recovery_note_when_verbose_false_on_failure(self) -> None:
        """Verify RecoveryNote is emitted when verbose=False and gates fail."""
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["foo.py"]
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "ruff",
                    "passed": False,
                    "status": "failed",
                    "details": "",
                }
            ],
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        context = NoteContext()
        await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"], verbose=False), context
        )

        notes = [
            n for n in context.of_type(Note) if n.key == "quality_gates_failed_verbose_suggestion"
        ]
        assert len(notes) == 1
        assert "scope='files'" in notes[0].params.get("scope_part", "")
        assert "foo.py" in notes[0].params.get("scope_part", "")

    @pytest.mark.asyncio
    async def test_no_recovery_note_when_verbose_true_on_failure(self) -> None:
        """Verify no RecoveryNote is emitted when verbose=True and gates fail."""
        mock_manager = MagicMock()
        mock_manager.resolve_scope.return_value = ["foo.py"]
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "ruff",
                    "passed": False,
                    "status": "failed",
                    "details": "Linter failed!",
                }
            ],
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        context = NoteContext()
        await tool.execute(
            RunQualityGatesInput(scope="files", files=["foo.py"], verbose=True), context
        )

        notes = [
            n for n in context.of_type(Note) if n.key == "quality_gates_failed_verbose_suggestion"
        ]
        assert len(notes) == 0


class TestStructuredGateFindings:
    """Public structured finding contract for run_quality_gates."""

    def test_finding_dto_is_frozen_serializable_and_forbids_extras(self) -> None:
        """The public finding is immutable, complete, and closed to unknown fields."""
        finding = tool_outputs.GateFindingDTO(gate="ruff", message="Invalid import order")

        assert finding.model_dump(mode="json") == {
            "gate": "ruff",
            "message": "Invalid import order",
            "file": None,
            "line": None,
            "column": None,
            "code": None,
            "severity": None,
            "fixable": False,
            "details": None,
        }
        with pytest.raises(ValidationError):
            finding.message = "changed"  # type: ignore[misc]
        with pytest.raises(ValidationError):
            tool_outputs.GateFindingDTO.model_validate(
                {
                    "gate": "ruff",
                    "message": "Invalid import order",
                    "unexpected": "not allowed",
                }
            )

    @pytest.mark.asyncio
    async def test_maps_ordered_full_and_message_only_findings(self) -> None:
        """The tool losslessly adapts manager issues without reclassifying them."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": False,
            "gates": [
                {
                    "name": "ruff",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "details": "raw ruff output",
                    "issues": [
                        {
                            "file": "mcp_server/example.py",
                            "line": 12,
                            "col": 7,
                            "rule": "E501",
                            "message": "Line too long",
                            "severity": "error",
                            "fixable": True,
                            "details": "line 12 exceeded the configured limit",
                        },
                        {"message": "ruff executable unavailable"},
                    ],
                },
                {
                    "name": "mypy",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                },
            ],
        }

        result = await RunQualityGatesTool(manager=mock_manager).execute(
            RunQualityGatesInput(scope="files", files=["mcp_server/example.py"]),
            NoteContext(),
        )

        assert [gate.name for gate in result.gates] == ["ruff", "mypy"]
        assert result.gates[0].details == "raw ruff output"
        assert [finding.message for finding in result.gates[0].findings] == [
            "Line too long",
            "ruff executable unavailable",
        ]
        assert result.gates[0].findings[0].model_dump(mode="json") == {
            "gate": "ruff",
            "message": "Line too long",
            "file": "mcp_server/example.py",
            "line": 12,
            "column": 7,
            "code": "E501",
            "severity": "error",
            "fixable": True,
            "details": "line 12 exceeded the configured limit",
        }
        assert result.gates[0].findings[1].model_dump(mode="json") == {
            "gate": "ruff",
            "message": "ruff executable unavailable",
            "file": None,
            "line": None,
            "column": None,
            "code": None,
            "severity": None,
            "fixable": False,
            "details": None,
        }
        assert result.gates[1].findings == []
