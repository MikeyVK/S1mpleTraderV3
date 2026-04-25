# pyright: reportPrivateUsage=false
"""Unit tests for test_tools.py.

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.tools.test_tools]
"""

import subprocess
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.config.settings import Settings
from mcp_server.core.operation_notes import InfoNote, NoteContext, RecoveryNote, SuggestionNote
from mcp_server.managers.pytest_runner import FailureDetail, PytestResult
from mcp_server.tools.test_tools import RunTestsInput, RunTestsTool
from tests.mcp_server.fixtures.fake_pytest_runner import FakePytestRunner

# ---------------------------------------------------------------------------
# Realistic pytest stdout fixtures for C1 tests
# ---------------------------------------------------------------------------

_PYTEST_STDOUT_GREEN = (
    "collected 2 items\n"
    "\n"
    "tests/unit/test_foo.py::test_one PASSED\n"
    "tests/unit/test_foo.py::test_two PASSED\n"
    "\n"
    "============================== 2 passed in 0.45s ==============================\n"
)

_PYTEST_STDOUT_RED = (
    "collected 5 items\n"
    "\n"
    "FAILED tests/unit/test_foo.py::test_bar - AssertionError: expected 1 got 2\n"
    "FAILED tests/unit/test_baz.py::test_qux - ValueError: something went wrong\n"
    "\n"
    "============================== 2 failed, 3 passed in 1.23s ==============================\n"
)


@pytest.fixture
def mock_run_pytest_sync() -> Generator[MagicMock, None, None]:
    """Patch the synchronous test runner."""
    with patch("mcp_server.tools.test_tools._run_pytest_sync") as mock:
        yield mock


@pytest.fixture
def injected_settings() -> Settings:
    """Provide explicit settings injection for RunTestsTool."""
    return Settings(server={"workspace_root": "/workspace"})


@pytest.mark.asyncio
async def test_run_tests_success(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    tool = RunTestsTool(settings=injected_settings)

    # Mock return: stdout, stderr, returncode
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["type"] == "text"
    assert result.content[1]["json"]["summary"]["passed"] == 1

    # Verify call args
    call_args = mock_run_pytest_sync.call_args
    assert call_args is not None
    cmd = call_args[0][0]
    assert "pytest" in cmd[2] or "pytest" in cmd[1]  # Depending on if run as module
    assert "tests/unit" in cmd


@pytest.mark.asyncio
async def test_run_tests_failure(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (
        "FAILED tests/foo.py::test_x - AssertionError: nope\n1 failed in 0.10s\n",
        "Error info",
        1,
    )

    result = await tool.execute(RunTestsInput(path="tests/foo.py"), NoteContext())

    assert result.content[0]["type"] == "text"
    assert result.content[1]["json"]["summary"]["failed"] == 1


@pytest.mark.asyncio
async def test_run_tests_markers(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = ("", "", 0)

    await tool.execute(RunTestsInput(path="tests/", markers="integration"), NoteContext())

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "-m" in cmd
    assert "integration" in cmd


@pytest.mark.asyncio
async def test_run_tests_exception(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.side_effect = OSError("Boom")

    result = await tool.execute(RunTestsInput(path="tests/"), NoteContext())

    assert result.is_error
    assert "Failed to run tests: Boom" in result.content[0]["text"]


# ---------------------------------------------------------------------------
# C1 RED: unix-style JSON response
# ---------------------------------------------------------------------------


def test_parse_pytest_output_importable() -> None:
    """_parse_pytest_output must be importable from test_tools."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    assert callable(_parse_pytest_output)


def test_parse_pytest_output_green() -> None:
    """Green run: summary with failed=0, no failures list."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_GREEN)

    assert result["summary"]["passed"] == 2
    assert result["summary"]["failed"] == 0
    assert result.get("failures", []) == []


def test_parse_pytest_output_red() -> None:
    """Red run: summary with failed count, each failure has test_id/short_reason/location."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_RED)

    assert result["summary"]["failed"] == 2
    assert len(result["failures"]) == 2
    failure = result["failures"][0]
    assert "test_id" in failure
    assert "short_reason" in failure
    assert "location" in failure


@pytest.mark.asyncio
async def test_run_tests_json_response_on_success(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """Successful run: content[0] is text summary, content[1] is JSON with summary.failed==0."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_GREEN, "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["type"] == "text"
    assert result.content[1]["json"]["summary"]["failed"] == 0
    assert result.content[1]["json"].get("failures", []) == []
    assert result.content[1]["type"] == "json"


@pytest.mark.asyncio
async def test_run_tests_json_response_on_failure(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """Failed run: content[0] is text summary, content[1] is JSON with failures list."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_RED, "", 1)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["type"] == "text"
    data = result.content[1]["json"]
    assert data["summary"]["failed"] == 2
    assert len(data["failures"]) == 2
    f = data["failures"][0]
    assert "test_id" in f
    assert "short_reason" in f
    assert "location" in f
    assert result.content[1]["type"] == "json"


def test_run_tests_input_has_no_verbose_field() -> None:
    """verbose field must be removed from RunTestsInput (unix-style: no output_mode)."""
    assert "verbose" not in RunTestsInput.model_fields


# ---------------------------------------------------------------------------
# C2 RED: last_failed_only parameter + _build_cmd extraction
# ---------------------------------------------------------------------------


def test_run_tests_input_has_last_failed_only_field() -> None:
    """RunTestsInput must have last_failed_only field defaulting to False."""
    assert "last_failed_only" in RunTestsInput.model_fields
    field_info = RunTestsInput.model_fields["last_failed_only"]
    assert field_info.default is False


def test_build_cmd_method_exists_on_tool() -> None:
    """_build_cmd must be a callable method on RunTestsTool."""
    assert callable(getattr(RunTestsTool, "_build_cmd", None))


@pytest.mark.asyncio
async def test_last_failed_only_adds_lf_flag(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """last_failed_only=True must add --lf to the subprocess command."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/", last_failed_only=True), NoteContext())

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "--lf" in cmd


@pytest.mark.asyncio
async def test_last_failed_only_default_no_lf_flag(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """Default (last_failed_only=False) must NOT add --lf."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/"), NoteContext())

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "--lf" not in cmd


@pytest.mark.asyncio
async def test_last_failed_only_combined_with_path(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """last_failed_only=True combined with path: both --lf and path present in cmd."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=True), NoteContext())

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "--lf" in cmd
    assert "tests/unit" in cmd


# ---------------------------------------------------------------------------
# C5 RED: path as space-separated str + scope="full" + mutual exclusion validation
# ---------------------------------------------------------------------------


def test_path_accepts_space_separated_string() -> None:
    """RunTestsInput must accept multiple paths as a space-separated string."""
    from pydantic import ValidationError  # noqa: PLC0415

    try:
        inp = RunTestsInput(path="tests/unit/test_a.py tests/unit/test_b.py")
    except (ValidationError, TypeError):
        pytest.fail("RunTestsInput should accept path as space-separated string")
    assert inp.path == "tests/unit/test_a.py tests/unit/test_b.py"


def test_scope_full_field_exists_and_is_accepted() -> None:
    """RunTestsInput must accept scope='full' without ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    try:
        inp = RunTestsInput(scope="full")
    except (ValidationError, TypeError):
        pytest.fail("RunTestsInput should accept scope='full'")
    assert inp.scope == "full"  # type: ignore[attr-defined]


def test_no_path_no_scope_raises_validation_error() -> None:
    """RunTestsInput() without path or scope must raise ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        RunTestsInput()


def test_path_and_scope_mutual_exclusion_raises_validation_error() -> None:
    """Providing both path and scope must raise ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        RunTestsInput(path="tests/unit.py", scope="full")


@pytest.mark.asyncio
async def test_space_separated_paths_produce_multiple_args_in_cmd(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """path='a.py b.py' must result in both paths as separate cmd args."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = ("2 passed in 0.20s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/test_a.py tests/test_b.py"), NoteContext())

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "tests/test_a.py" in cmd
    assert "tests/test_b.py" in cmd


@pytest.mark.asyncio
async def test_scope_full_produces_no_path_args_in_cmd(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """scope='full' must run pytest without any explicit path arguments."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = ("10 passed in 1.00s\n", "", 0)

    await tool.execute(RunTestsInput(scope="full"), NoteContext())

    cmd = mock_run_pytest_sync.call_args[0][0]
    # cmd should not contain any test path arguments (only flags/options)
    path_like = [
        arg for arg in cmd if not arg.startswith("-") and arg not in (cmd[0], cmd[1], cmd[2])
    ]
    assert path_like == [], f"Expected no path args for scope='full', got: {path_like}"


# ---------------------------------------------------------------------------
# C6 RED: summary_line in output + text content = summary_line
# ---------------------------------------------------------------------------

_PYTEST_STDOUT_WITH_TB_SHORT = (
    "collected 1 item\n"
    "\n"
    "FAILED tests/unit/test_foo.py::test_bar\n"
    "\n"
    "=========================== FAILURES ===========================\n"
    "___________________________ test_bar ___________________________\n"
    "\n"
    "    def test_bar():\n"
    ">       assert 1 == 2\n"
    "E   AssertionError: assert 1 == 2\n"
    "\n"
    "tests/unit/test_foo.py:5: AssertionError\n"
    "FAILED tests/unit/test_foo.py::test_bar - AssertionError: assert 1 == 2\n"
    "\n"
    "============================== 1 failed in 0.10s ==============================\n"
)


def test_parse_pytest_output_returns_summary_line() -> None:
    """_parse_pytest_output must return a 'summary_line' key with human-readable text."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_GREEN)

    assert "summary_line" in result


def test_parse_pytest_output_summary_line_content() -> None:
    """summary_line must be the '... passed in ...' line from pytest output."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_GREEN)

    assert "2 passed" in result["summary_line"]
    assert "0.45s" in result["summary_line"]


def test_parse_pytest_output_summary_line_on_failure() -> None:
    """summary_line must contain 'failed' when tests fail."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_RED)

    assert "failed" in result["summary_line"]
    assert "passed" in result["summary_line"]


@pytest.mark.asyncio
async def test_run_tests_text_content_is_summary_line(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """content[0]['text'] must be the summary_line, not json.dumps of the full response."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_GREEN, "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    text = result.content[0]["text"]
    # Must be summary line, not a JSON blob
    assert not text.startswith("{"), f"content[0]['text'] should be summary_line not JSON: {text!r}"
    assert "passed" in text


@pytest.mark.asyncio
async def test_run_tests_text_content_is_summary_line_on_failure(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """content[0]['text'] must be the summary_line even when tests fail."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_RED, "", 1)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    text = result.content[0]["text"]
    assert not text.startswith("{"), f"content[0]['text'] should be summary_line not JSON: {text!r}"
    assert "failed" in text


# ---------------------------------------------------------------------------
# C6 RED (D6.2): traceback in failure items
# ---------------------------------------------------------------------------


def test_parse_pytest_output_failure_has_traceback_key() -> None:
    """Each failure item must contain a 'traceback' key."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_WITH_TB_SHORT)

    assert len(result["failures"]) == 1
    failure = result["failures"][0]
    assert "traceback" in failure


def test_parse_pytest_output_traceback_contains_assertion_error() -> None:
    """The 'traceback' value must contain the --tb=short block for the failure."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_WITH_TB_SHORT)

    traceback = result["failures"][0]["traceback"]
    assert "AssertionError" in traceback
    assert "assert 1 == 2" in traceback


# ---------------------------------------------------------------------------
# C29 RED: invert run_tests content order — text first, json second
# Must fail until GREEN inverts the order in test_tools.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_tests_content0_is_text_summary(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """C29 contract: content[0] must be the text summary line (not json)."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_GREEN, "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["type"] == "text", (
        f"Expected content[0] type='text', got '{result.content[0]['type']}'"
    )


@pytest.mark.asyncio
async def test_run_tests_content1_is_json_payload(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """C29 contract: content[1] must be the json payload (not text)."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_RED, "", 1)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[1]["type"] == "json", (
        f"Expected content[1] type='json', got '{result.content[1]['type']}'"
    )
    assert "summary" in result.content[1]["json"]


@pytest.mark.asyncio
async def test_run_tests_content0_text_contains_summary_line(
    mock_run_pytest_sync: MagicMock, injected_settings: Settings
) -> None:
    """C29 contract: content[0].text is the human-readable summary line."""
    tool = RunTestsTool(settings=injected_settings)
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_GREEN, "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert isinstance(result.content[0].get("text", None), str)
    assert len(result.content[0]["text"]) > 0


# ---------------------------------------------------------------------------
# C4 RED: thin adapter with injected runner + typed notes/coverage contract
# ---------------------------------------------------------------------------


def _make_pytest_result(
    *,
    exit_code: int = 0,
    summary_line: str = "1 passed in 0.10s",
    passed: int = 1,
    failed: int = 0,
    skipped: int = 0,
    errors: int = 0,
    failures: tuple[FailureDetail, ...] = (),
    coverage_pct: float | None = None,
    lf_cache_was_empty: bool = False,
    should_raise: bool = False,
    note: RecoveryNote | SuggestionNote | InfoNote | None = None,
) -> PytestResult:
    return PytestResult(
        exit_code=exit_code,
        summary_line=summary_line,
        passed=passed,
        failed=failed,
        skipped=skipped,
        errors=errors,
        failures=failures,
        coverage_pct=coverage_pct,
        lf_cache_was_empty=lf_cache_was_empty,
        should_raise=should_raise,
        note=note,
    )


class _TimeoutPytestRunner:
    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult:
        del cwd
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)


class _OSErrorPytestRunner:
    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult:
        del cmd, cwd, timeout
        raise OSError("Boom")


@pytest.mark.asyncio
async def test_c4_run_tests_all_passed_via_injected_runner(injected_settings: Settings) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(summary_line="2 passed in 0.45s", passed=2)
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.content[0]["text"] == "2 passed in 0.45s"
    assert result.content[1]["json"]["summary"]["passed"] == 2
    assert len(context.of_type(RecoveryNote)) == 0


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
            summary_line="1 failed, 2 passed in 0.20s",
            passed=2,
            failed=1,
            failures=(failure,),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[1]["json"]["summary"]["failed"] == 1
    assert len(result.content[1]["json"]["failures"]) == 1
    assert result.content[1]["json"]["failures"][0]["test_id"] == failure.test_id


@pytest.mark.asyncio
async def test_c4_run_tests_interrupted_returns_error_result(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=2,
            summary_line="pytest interrupted (exit 2)",
            should_raise=True,
            note=RecoveryNote("Pytest was interrupted; check for hung tests or external SIGINT."),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert "returncode 2" in result.content[0]["text"]
    assert len(context.of_type(RecoveryNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_internal_error_returns_error_result(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=3,
            summary_line="pytest internal error (exit 3)",
            should_raise=True,
            note=RecoveryNote(
                "Pytest reported an internal error; inspect stderr and pytest plugins."
            ),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert "returncode 3" in result.content[0]["text"]
    assert len(context.of_type(RecoveryNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_usage_error_returns_error_result(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=4,
            summary_line="pytest usage error (exit 4)",
            should_raise=True,
            note=RecoveryNote(
                "Pytest could not start. Verify the path exists and the CLI options are valid."
            ),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert "returncode 4" in result.content[0]["text"]
    assert len(context.of_type(RecoveryNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_no_tests_collected_returns_suggestion_note(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=5,
            summary_line="no tests collected",
            passed=0,
            failed=0,
            note=SuggestionNote("No tests matched the filter. Check markers and path."),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.content[0]["text"] == "no tests collected"
    assert len(context.of_type(SuggestionNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_unknown_exit_code_returns_error_result(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(
            exit_code=99,
            summary_line="pytest exited with unexpected code",
            should_raise=True,
            note=RecoveryNote("Pytest exited with unexpected code 99; inspect stderr."),
        )
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert "returncode 99" in result.content[0]["text"]
    assert len(context.of_type(RecoveryNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_lf_empty_emits_info_note_when_requested(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(lf_cache_was_empty=True))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=True), context)

    assert len(context.of_type(InfoNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_lf_cache_populated_emits_no_info_note(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(lf_cache_was_empty=False))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=True), context)

    assert len(context.of_type(InfoNote)) == 0


@pytest.mark.asyncio
async def test_c4_run_tests_lf_flag_ignored_when_not_requested(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(lf_cache_was_empty=True))
    tool = RunTestsTool(runner=runner, settings=injected_settings)
    context = NoteContext()

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=False), context)

    assert len(context.of_type(InfoNote)) == 0


@pytest.mark.asyncio
async def test_c4_run_tests_coverage_true_roundtrips_json(injected_settings: Settings) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(coverage_pct=92.5))
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit", coverage=True), NoteContext())

    assert result.content[1]["json"]["coverage_pct"] == pytest.approx(92.5)


@pytest.mark.asyncio
async def test_c4_run_tests_coverage_false_roundtrips_none(injected_settings: Settings) -> None:
    runner = FakePytestRunner(result=_make_pytest_result(coverage_pct=None))
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit", coverage=False), NoteContext())

    assert result.content[1]["json"]["coverage_pct"] is None


@pytest.mark.asyncio
async def test_c4_run_tests_text_and_json_summary_stay_in_sync(
    injected_settings: Settings,
) -> None:
    runner = FakePytestRunner(
        result=_make_pytest_result(summary_line="3 passed in 0.30s", passed=3)
    )
    tool = RunTestsTool(runner=runner, settings=injected_settings)

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["text"] == result.content[1]["json"]["summary_line"]


@pytest.mark.asyncio
async def test_c4_run_tests_timeout_returns_error_result(
    injected_settings: Settings,
) -> None:
    tool = RunTestsTool(runner=_TimeoutPytestRunner(), settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit", timeout=12), context)

    assert result.is_error is True
    assert "timed out" in result.content[0]["text"].lower()
    assert len(context.of_type(RecoveryNote)) == 1


@pytest.mark.asyncio
async def test_c4_run_tests_oserror_returns_error_result(
    injected_settings: Settings,
) -> None:
    tool = RunTestsTool(runner=_OSErrorPytestRunner(), settings=injected_settings)
    context = NoteContext()

    result = await tool.execute(RunTestsInput(path="tests/unit"), context)

    assert result.is_error is True
    assert "Failed to run tests: Boom" in result.content[0]["text"]
    assert len(context.of_type(RecoveryNote)) == 1


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
