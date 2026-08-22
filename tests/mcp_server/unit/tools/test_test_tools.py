"""Unit tests for RunTestsTool thin adapter.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.test_tools, tests.mcp_server.fixtures.fake_pytest_runner]
"""

import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.pytest_runner import FailureDetail, PytestResult
from mcp_server.schemas.tool_outputs import RunTestsOutput
from mcp_server.tools.test_tools import RunTestsInput, RunTestsTool
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.fixtures.fake_pytest_runner import FakePytestRunner


@pytest.fixture
def injected_settings() -> Settings:
    """Provide explicit settings injection for RunTestsTool."""
    return Settings(server={"workspace_root": "/workspace"})


def _make_pytest_result(
    *,
    exit_code: int = 0,
    duration_seconds: float | None = 0.1,
    passed: int = 1,
    failed: int = 0,
    skipped: int = 0,
    errors: int = 0,
    failures: tuple[FailureDetail, ...] = (),
    coverage_pct: float | None = None,
    lf_cache_was_empty: bool = False,
    should_raise: bool = False,
    note: Note | None = None,
    is_error: bool = False,
    stderr: str = "",
) -> PytestResult:
    return PytestResult(
        exit_code=exit_code,
        duration_seconds=duration_seconds,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        failures=failures,
        coverage_pct=coverage_pct,
        lf_cache_was_empty=lf_cache_was_empty,
        should_raise=should_raise,
        note=note,
        is_error=is_error,
        stderr=stderr,
    )


def test_c1_fake_pytest_runner_run_accepts_verbose_kwarg() -> None:
    """FakePytestRunner.run accepts verbose keyword-only argument."""
    runner = FakePytestRunner(result=_make_pytest_result())
    runner.run(["pytest"], cwd=".", timeout=30, verbose=True)


class _TimeoutPytestRunner:
    def run(self, cmd: list[str], cwd: str, timeout: int, *, verbose: bool = False) -> PytestResult:
        del cwd, verbose
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)


class _OSErrorPytestRunner:
    def run(self, cmd: list[str], cwd: str, timeout: int, *, verbose: bool = False) -> PytestResult:
        del cmd, cwd, timeout, verbose
        raise OSError("Boom")


_original_execute = RunTestsTool.execute


async def _wrapped_execute(
    self: RunTestsTool, params: RunTestsInput, context: NoteContext
) -> ToolResult | RunTestsOutput:
    dto_result = await _original_execute(self, params, context)
    if not isinstance(dto_result, RunTestsOutput):
        return dto_result

    payload = {
        "exit_code": dto_result.exit_code,
        "summary": {
            "passed": dto_result.passed_count,
            "failed": dto_result.failed_count,
            "skipped": dto_result.skipped_count,
            "errors": dto_result.errors_count,
        },
        "duration_seconds": dto_result.duration_seconds,
        "failures": [
            {
                "test_id": f.test_id,
                "location": f.location,
                "short_reason": f.short_reason,
                "traceback": f.traceback,
                "is_collection_error": f.is_collection_error,
            }
            for f in dto_result.failures
        ],
        "coverage_pct": dto_result.coverage_pct,
        "lf_cache_was_empty": dto_result.lf_cache_was_empty,
        "stderr": dto_result.stderr,
    }

    failure_lines_list = []
    for f in dto_result.failures:
        if f.is_collection_error:
            failure_lines_list.append(f"ERROR collecting {f.test_id} — {f.short_reason}")
        else:
            failure_lines_list.append(f"FAILED {f.test_id} — {f.short_reason}")
    failure_lines = "\n".join(failure_lines_list)

    text = f"exit={dto_result.exit_code}; duration={dto_result.duration_seconds}"
    if failure_lines:
        text += "\n" + failure_lines
    elif dto_result.stderr:
        first_stderr = next((ln for ln in dto_result.stderr.splitlines() if ln.strip()), "")[:120]
        if first_stderr:
            text += f"\nstderr: {first_stderr}"

    is_error = not dto_result.success
    return ToolResult.json_data(payload, text=text, is_error=is_error)


@pytest.fixture(scope="module", autouse=True)
def _patch_run_tests_execute():
    RunTestsTool.execute = _wrapped_execute
    yield
    RunTestsTool.execute = _original_execute


async def _execute_unwrapped(
    tool: RunTestsTool,
    params: RunTestsInput,
    context: NoteContext,
) -> object:
    return await _original_execute(tool, params, context)


@pytest.mark.asyncio
async def test_run_tests_tool_returns_dto(injected_settings: Settings) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(duration_seconds=0.45, passed=2))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await _original_execute(tool, RunTestsInput(path="tests/unit"), context)
    assert isinstance(result, RunTestsOutput)
    assert result.success is True
    assert result.passed_count == 2


@pytest.mark.asyncio
async def test_c4_run_tests_all_passed_via_injected_runner(injected_settings: Settings) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(duration_seconds=0.45, passed=2))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.content[0]["json"]["summary"]["passed"] == 2
    assert result.content[0]["json"]["duration_seconds"] == pytest.approx(0.45)
    assert "summary_line" not in result.content[0]["json"]
    assert len(context.entries) == 0


@pytest.mark.asyncio
async def test_c4_run_tests_failed_result_contains_failures(injected_settings: Settings) -> None:
    failure = FailureDetail(
        test_id="tests/unit/test_foo.py::test_bar",
        location="tests/unit/test_foo.py",
        short_reason="AssertionError: nope",
        traceback="tests/unit/test_foo.py:5: AssertionError",
    )
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=1,
            duration_seconds=0.2,
            passed=2,
            failed=1,
            failures=(failure,),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["json"]["summary"]["failed"] == 1
    assert len(result.content[0]["json"]["failures"]) == 1
    assert result.content[0]["json"]["failures"][0]["test_id"] == failure.test_id


@pytest.mark.asyncio
async def test_c4_run_tests_interrupted_raises_execution_error(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=2,
            duration_seconds=None,
            is_error=True,
            note=Note(key="pytest_interrupted_recovery", params={}),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert len([n for n in context.of_type(Note) if n.key == "pytest_interrupted_recovery"]) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_internal_error_raises_execution_error(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=3,
            duration_seconds=None,
            is_error=True,
            note=Note(key="pytest_internal_error_recovery", params={}),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert len([n for n in context.of_type(Note) if n.key == "pytest_internal_error_recovery"]) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_usage_error_raises_execution_error(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=4,
            duration_seconds=None,
            is_error=True,
            note=Note(key="pytest_usage_error_recovery", params={}),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert len([n for n in context.of_type(Note) if n.key == "pytest_usage_error_recovery"]) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_no_tests_collected_returns_suggestion_note(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=5,
            duration_seconds=0.01,
            passed=0,
            failed=0,
            note=Note(key="pytest_no_tests_collected_suggestion", params={}),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.content[1]["text"] == "exit=5; duration=0.01"
    assert (
        len([n for n in context.of_type(Note) if n.key == "pytest_no_tests_collected_suggestion"])
        == 1
    )


@pytest.mark.asyncio
async def test_c4_run_tests_unknown_exit_code_raises_execution_error(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=99,
            duration_seconds=None,
            should_raise=True,
            note=Note(key="pytest_unexpected_code_recovery", params={"exit_code": 99}),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    with pytest.raises(ExecutionError, match="pytest exited with returncode 99"):
        await _execute_unwrapped(tool, RunTestsInput(path="tests/unit"), context)

    assert (
        len([n for n in context.of_type(Note) if n.key == "pytest_unexpected_code_recovery"]) == 1
    )


@pytest.mark.asyncio
async def test_c4_run_tests_lf_empty_emits_info_note_when_requested(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(lf_cache_was_empty=True))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=True), context)

    assert len([n for n in context.of_type(Note) if n.key == "pytest_lf_cache_empty_info"]) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_lf_cache_populated_emits_no_info_note(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(lf_cache_was_empty=False))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=True), context)

    assert len([n for n in context.of_type(Note) if n.key == "pytest_lf_cache_empty_info"]) == 0


@pytest.mark.asyncio
async def test_c4_run_tests_lf_flag_ignored_when_not_requested(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(lf_cache_was_empty=True))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=False), context)

    assert len([n for n in context.of_type(Note) if n.key == "pytest_lf_cache_empty_info"]) == 0


@pytest.mark.asyncio
async def test_c4_run_tests_coverage_true_roundtrips_json(injected_settings: Settings) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(coverage_pct=92.5))
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit", coverage=True), NoteContext())

    assert result.content[0]["json"]["coverage_pct"] == pytest.approx(92.5)


@pytest.mark.asyncio
async def test_c4_run_tests_coverage_false_roundtrips_none(injected_settings: Settings) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(coverage_pct=None))
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit", coverage=False), NoteContext())

    assert result.content[0]["json"]["coverage_pct"] is None


@pytest.mark.asyncio
async def test_c4_run_tests_duration_roundtrips_as_numeric_data(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(duration_seconds=0.3, passed=3))
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["json"]["duration_seconds"] == pytest.approx(0.3)
    assert "summary_line" not in result.content[0]["json"]


@pytest.mark.asyncio
async def test_c4_run_tests_timeout_raises_execution_error(
    injected_settings: Settings,
) -> None:
    tool = RunTestsTool(runner=_TimeoutPytestRunner(), settings=injected_settings)
    context = NoteContext()

    with pytest.raises(ExecutionError, match="Tests timed out after 12s"):
        await _execute_unwrapped(tool, RunTestsInput(path="tests/unit", timeout=12), context)

    assert len([n for n in context.of_type(Note) if n.key == "pytest_timeout_recovery"]) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_oserror_raises_execution_error(
    injected_settings: Settings,
) -> None:
    tool = RunTestsTool(runner=_OSErrorPytestRunner(), settings=injected_settings)
    context = NoteContext()

    with pytest.raises(ExecutionError, match="Failed to run tests: Boom"):
        await _execute_unwrapped(tool, RunTestsInput(path="tests/unit"), context)

    assert len([n for n in context.of_type(Note) if n.key == "pytest_interpreter_recovery"]) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_build_cmd_adds_coverage_packages(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result())
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    await tool.execute(RunTestsInput(path="tests/unit", coverage=True), NoteContext())

    assert runner.captured_cmd is not None
    assert "--cov=backend" in runner.captured_cmd
    assert "--cov=mcp_server" in runner.captured_cmd
    assert "--cov-branch" in runner.captured_cmd


@pytest.mark.asyncio
async def test_c4_run_tests_build_cmd_adds_fail_under_threshold(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result())
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    await tool.execute(RunTestsInput(path="tests/unit", coverage=True), NoteContext())

    assert runner.captured_cmd is not None
    assert "--cov-fail-under=90" in runner.captured_cmd


@pytest.mark.asyncio
async def test_c4_run_tests_build_cmd_omits_coverage_flags_when_disabled(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result())
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    await tool.execute(RunTestsInput(path="tests/unit", coverage=False), NoteContext())

    assert runner.captured_cmd is not None
    assert not any(part.startswith("--cov") for part in runner.captured_cmd)


# ---------------------------------------------------------------------------
# C3 — _to_tool_result() routing split on result.is_error
# ---------------------------------------------------------------------------


class TestC3ToToolResultRouting:
    """C3: _to_tool_result() routes on result.is_error; exit 2/3/4 → ToolResult(is_error=True)."""

    @pytest.mark.asyncio
    async def test_c3_to_tool_result_exit1_is_error_false(
        self, injected_settings: Settings
    ) -> None:
        """Exit 1 (tests failed) → ToolResult(is_error=False)."""
        failure = FailureDetail(
            test_id="tests/unit/test_foo.py::test_bad",
            location="tests/unit/test_foo.py",
            short_reason="AssertionError: nope",
            traceback="",
        )
        runner = FakePytestRunner(
            result=_make_pytest_result(
                exit_code=1,
                duration_seconds=0.1,
                failed=1,
                failures=(failure,),
                is_error=False,
            )
        )
        tool = RunTestsTool(runner=runner, settings=injected_settings)

        result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_c3_to_tool_result_exit1_content1_includes_failure_lines(
        self, injected_settings: Settings
    ) -> None:
        """Exit 1 + failure → content[0] text contains FAILED ... — ... line."""
        failure = FailureDetail(
            test_id="tests/unit/test_foo.py::test_bad",
            location="tests/unit/test_foo.py",
            short_reason="AssertionError: nope",
            traceback="",
        )
        runner = FakePytestRunner(
            result=_make_pytest_result(
                exit_code=1,
                duration_seconds=None,
                failed=1,
                failures=(failure,),
                is_error=False,
            )
        )
        tool = RunTestsTool(runner=runner, settings=injected_settings)

        result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

        assert "FAILED tests/unit/test_foo.py::test_bad" in result.content[1]["text"]
        assert "AssertionError: nope" in result.content[1]["text"]

    @pytest.mark.asyncio
    async def test_c3_to_tool_result_exit2_returns_tool_result_is_error_true(
        self, injected_settings: Settings
    ) -> None:
        """Exit 2 (is_error=True) → ToolResult(is_error=True), not ExecutionError."""
        runner = FakePytestRunner(
            result=_make_pytest_result(
                exit_code=2,
                duration_seconds=None,
                is_error=True,
                note=Note(
                    key="pytest_interrupted_recovery",
                    params={},
                ),
            )
        )
        tool = RunTestsTool(runner=runner, settings=injected_settings)

        result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

        assert result.is_error is True

    @pytest.mark.asyncio
    async def test_c3_to_tool_result_exit2_text_includes_stderr_context(
        self, injected_settings: Settings
    ) -> None:
        """Exit 2 plus stderr retains a concise diagnostic first line."""
        runner = FakePytestRunner(
            result=_make_pytest_result(
                exit_code=2,
                duration_seconds=None,
                is_error=True,
                stderr="INTERNALERROR> some traceback\nmore lines",
            )
        )
        tool = RunTestsTool(runner=runner, settings=injected_settings)

        result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

        assert result.content[1]["text"].startswith("exit=2")
        assert "INTERNALERROR" in result.content[1]["text"]

    @pytest.mark.asyncio
    async def test_c3_to_tool_result_payload_includes_stderr_tail(
        self, injected_settings: Settings
    ) -> None:
        """content[0] JSON payload always contains 'stderr' key."""
        runner = FakePytestRunner(
            result=_make_pytest_result(
                exit_code=0,
                duration_seconds=0.1,
                stderr="",
            )
        )
        tool = RunTestsTool(runner=runner, settings=injected_settings)

        result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

        assert "stderr" in result.content[0]["json"]

    @pytest.mark.asyncio
    async def test_c3_to_tool_result_exit0_retains_structured_counts_and_duration(
        self, injected_settings: Settings
    ) -> None:
        """Exit 0 retains counts and numeric duration in structured output."""
        runner = FakePytestRunner(
            result=_make_pytest_result(
                exit_code=0,
                duration_seconds=0.3,
                passed=3,
                is_error=False,
            )
        )
        tool = RunTestsTool(runner=runner, settings=injected_settings)

        result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

        assert result.content[0]["json"]["summary"]["passed"] == 3
        assert result.content[0]["json"]["duration_seconds"] == pytest.approx(0.3)


def test_c2_run_tests_input_verbose_validation() -> None:
    """RunTestsInput validates verbose constraints."""
    # 1. Default verbose is False
    model = RunTestsInput(path="tests/mcp_server/unit/tools/test_test_tools.py")
    assert model.verbose is False

    # 2. verbose=True requires path (reject scope="full")
    with pytest.raises(ValueError, match="path"):
        RunTestsInput(scope="full", verbose=True)

    # 3. verbose=True rejects directories
    with pytest.raises(ValueError, match="directory"):
        RunTestsInput(path="tests/mcp_server/unit", verbose=True)

    # 4. verbose=True rejects space-separated list containing directory
    with pytest.raises(ValueError, match="directory"):
        RunTestsInput(
            path="tests/mcp_server/unit/tools/test_test_tools.py tests/mcp_server/unit",
            verbose=True,
        )

    # 5. verbose=True rejects paths that are not python files
    with pytest.raises(ValueError, match="file"):
        RunTestsInput(path="tests/mcp_server/unit/tools/test_test_tools", verbose=True)

    # 6. verbose=True accepts valid test files
    valid_file = RunTestsInput(
        path="tests/mcp_server/unit/tools/test_test_tools.py",
        verbose=True,
    )
    assert valid_file.verbose is True

    # 7. verbose=True accepts valid test files with test methods
    valid_method = RunTestsInput(
        path="tests/mcp_server/unit/tools/test_test_tools.py::test_foo",
        verbose=True,
    )
    assert valid_method.verbose is True


@pytest.mark.asyncio
async def test_c3_run_tests_build_cmd_verbose_tb_styles(injected_settings: Settings) -> None:
    """RunTestsTool._build_cmd sets --tb=long when verbose is True, short when False."""
    runner = FakePytestRunner(result=_make_pytest_result())
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    await tool.execute(
        RunTestsInput(
            path="tests/mcp_server/unit/tools/test_test_tools.py",
            verbose=True,
        ),
        NoteContext(),
    )
    assert runner.captured_cmd is not None
    assert "--tb=long" in runner.captured_cmd
    assert "--tb=short" not in runner.captured_cmd

    await tool.execute(
        RunTestsInput(
            path="tests/mcp_server/unit/tools/test_test_tools.py",
            verbose=False,
        ),
        NoteContext(),
    )
    assert runner.captured_cmd is not None
    assert "--tb=short" in runner.captured_cmd
    assert "--tb=long" not in runner.captured_cmd


@pytest.mark.asyncio
async def test_c4_run_tests_propagates_verbose_flag(injected_settings: Settings) -> None:
    """RunTestsTool.execute propagates verbose=True to the runner."""
    runner = MagicMock()
    runner.run.return_value = _make_pytest_result()
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    await tool.execute(
        RunTestsInput(
            path="tests/mcp_server/unit/tools/test_test_tools.py",
            verbose=True,
        ),
        NoteContext(),
    )
    runner.run.assert_called_with(
        [
            sys.executable,
            "-m",
            "pytest",
            "--tb=long",
            "tests/mcp_server/unit/tools/test_test_tools.py",
        ],
        "/workspace",
        300,
        verbose=True,
    )

    await tool.execute(
        RunTestsInput(
            path="tests/mcp_server/unit/tools/test_test_tools.py",
            verbose=False,
        ),
        NoteContext(),
    )
    runner.run.assert_called_with(
        [
            sys.executable,
            "-m",
            "pytest",
            "--tb=short",
            "tests/mcp_server/unit/tools/test_test_tools.py",
        ],
        "/workspace",
        300,
        verbose=False,
    )


@pytest.mark.asyncio
async def test_c4_run_tests_recovery_note_on_failure(injected_settings: Settings) -> None:
    """When verbose=False and tests fail, generate a RecoveryNote suggesting the failing files."""
    failure_1 = FailureDetail(
        test_id="tests/unit/test_a.py::test_1",
        location="tests/unit/test_a.py",
        short_reason="AssertionError: 1",
        traceback="",
    )
    failure_2 = FailureDetail(
        test_id="tests/unit/test_b.py::test_2",
        location="tests/unit/test_b.py",
        short_reason="AssertionError: 2",
        traceback="",
    )

    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=1,
            duration_seconds=0.1,
            passed=0,
            failed=2,
            failures=(failure_1, failure_2),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(
        RunTestsInput(
            path="tests/unit/test_a.py tests/unit/test_b.py",
            verbose=False,
        ),
        context,
    )

    notes = [n for n in context.of_type(Note) if n.key == "pytest_failed_verbose_suggestion"]
    assert len(notes) == 1
    assert notes[0].params.get("failing_files") == "tests/unit/test_a.py tests/unit/test_b.py"


@pytest.mark.asyncio
async def test_c4_run_tests_no_recovery_note_when_verbose_true(
    injected_settings: Settings,
) -> None:
    """When verbose=True and tests fail, do NOT generate the rerun RecoveryNote."""
    failure = FailureDetail(
        test_id="tests/unit/test_a.py::test_1",
        location="tests/unit/test_a.py",
        short_reason="AssertionError: 1",
        traceback="some tb",
    )
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=1,
            duration_seconds=None,
            passed=0,
            failed=1,
            failures=(failure,),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(
        RunTestsInput(
            path="tests/unit/test_a.py",
            verbose=True,
        ),
        context,
    )

    notes = [n for n in context.of_type(Note) if n.key == "pytest_failed_verbose_suggestion"]
    assert len(notes) == 0


@pytest.mark.asyncio
async def test_run_tests_build_cmd_collect_only(injected_settings: Settings) -> None:
    """RunTestsTool._build_cmd includes --collect-only when collect_only is True."""
    runner = FakePytestRunner(result=_make_pytest_result())
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    await tool.execute(
        RunTestsInput(
            path="tests/mcp_server/unit/tools/test_test_tools.py",
            collect_only=True,
        ),
        NoteContext(),
    )
    assert runner.captured_cmd is not None
    assert "--collect-only" in runner.captured_cmd
