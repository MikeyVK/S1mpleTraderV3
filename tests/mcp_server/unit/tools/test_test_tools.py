"""Unit tests for test_tools.py."""

from unittest.mock import patch

import pytest

from mcp_server.tools.test_tools import RunTestsInput, RunTestsTool

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
def mock_run_pytest_sync():
    """Patch the synchronous test runner."""
    with patch("mcp_server.tools.test_tools._run_pytest_sync") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    with patch("mcp_server.tools.test_tools.settings") as mock:
        mock.server.workspace_root = "/workspace"
        yield mock


@pytest.mark.asyncio
async def test_run_tests_success(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()

    # Mock return: stdout, stderr, returncode
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"))

    assert result.content[0]["type"] == "json"
    assert result.content[0]["json"]["summary"]["passed"] == 1

    # Verify call args
    call_args = mock_run_pytest_sync.call_args
    assert call_args is not None
    cmd = call_args[0][0]
    assert "pytest" in cmd[2] or "pytest" in cmd[1]  # Depending on if run as module
    assert "tests/unit" in cmd


@pytest.mark.asyncio
async def test_run_tests_failure(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = (
        "FAILED tests/foo.py::test_x - AssertionError: nope\n1 failed in 0.10s\n",
        "Error info",
        1,
    )

    result = await tool.execute(RunTestsInput(path="tests/foo.py"))

    assert result.content[0]["type"] == "json"
    assert result.content[0]["json"]["summary"]["failed"] == 1


@pytest.mark.asyncio
async def test_run_tests_markers(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("", "", 0)

    await tool.execute(RunTestsInput(path="tests/", markers="integration"))

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "-m" in cmd
    assert "integration" in cmd


@pytest.mark.asyncio
async def test_run_tests_exception(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()
    mock_run_pytest_sync.side_effect = OSError("Boom")

    result = await tool.execute(RunTestsInput(path="tests/"))

    assert result.is_error
    assert "Failed to run tests: Boom" in result.content[0]["text"]


# ---------------------------------------------------------------------------
# C1 RED: unix-style JSON response
# ---------------------------------------------------------------------------


def test_parse_pytest_output_importable():
    """_parse_pytest_output must be importable from test_tools."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    assert callable(_parse_pytest_output)


def test_parse_pytest_output_green():
    """Green run: summary with failed=0, no failures list."""
    from mcp_server.tools.test_tools import _parse_pytest_output  # noqa: PLC0415

    result = _parse_pytest_output(_PYTEST_STDOUT_GREEN)

    assert result["summary"]["passed"] == 2
    assert result["summary"]["failed"] == 0
    assert result.get("failures", []) == []


def test_parse_pytest_output_red():
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
async def test_run_tests_json_response_on_success(mock_run_pytest_sync, mock_settings):
    """Successful run: content[0] is JSON with summary.failed==0, content[1] is text fallback."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_GREEN, "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit"))

    assert result.content[0]["type"] == "json"
    assert result.content[0]["json"]["summary"]["failed"] == 0
    assert result.content[0]["json"].get("failures", []) == []
    assert result.content[1]["type"] == "text"


@pytest.mark.asyncio
async def test_run_tests_json_response_on_failure(mock_run_pytest_sync, mock_settings):
    """Failed run: content[0] is JSON with failures list, content[1] is text fallback."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = (_PYTEST_STDOUT_RED, "", 1)

    result = await tool.execute(RunTestsInput(path="tests/unit"))

    assert result.content[0]["type"] == "json"
    data = result.content[0]["json"]
    assert data["summary"]["failed"] == 2
    assert len(data["failures"]) == 2
    f = data["failures"][0]
    assert "test_id" in f
    assert "short_reason" in f
    assert "location" in f
    assert result.content[1]["type"] == "text"


def test_run_tests_input_has_no_verbose_field():
    """verbose field must be removed from RunTestsInput (unix-style: no output_mode)."""
    assert "verbose" not in RunTestsInput.model_fields


# ---------------------------------------------------------------------------
# C2 RED: last_failed_only parameter + _build_cmd extraction
# ---------------------------------------------------------------------------


def test_run_tests_input_has_last_failed_only_field():
    """RunTestsInput must have last_failed_only field defaulting to False."""
    assert "last_failed_only" in RunTestsInput.model_fields
    field_info = RunTestsInput.model_fields["last_failed_only"]
    assert field_info.default is False


def test_build_cmd_method_exists_on_tool():
    """_build_cmd must be a callable method on RunTestsTool."""
    assert callable(getattr(RunTestsTool, "_build_cmd", None))


@pytest.mark.asyncio
async def test_last_failed_only_adds_lf_flag(mock_run_pytest_sync, mock_settings):
    """last_failed_only=True must add --lf to the subprocess command."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/", last_failed_only=True))  # type: ignore[call-arg]

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "--lf" in cmd


@pytest.mark.asyncio
async def test_last_failed_only_default_no_lf_flag(mock_run_pytest_sync, mock_settings):
    """Default (last_failed_only=False) must NOT add --lf."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/"))

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "--lf" not in cmd


@pytest.mark.asyncio
async def test_last_failed_only_combined_with_path(mock_run_pytest_sync, mock_settings):
    """last_failed_only=True combined with path: both --lf and path present in cmd."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("1 passed in 0.10s\n", "", 0)

    await tool.execute(RunTestsInput(path="tests/unit", last_failed_only=True))  # type: ignore[call-arg]

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "--lf" in cmd
    assert "tests/unit" in cmd


# ---------------------------------------------------------------------------
# C5 RED: path as list[str] + scope="full" + mutual exclusion validation
# ---------------------------------------------------------------------------


def test_path_accepts_list_of_strings():
    """RunTestsInput must accept path as list[str] without ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    try:
        inp = RunTestsInput(path=["tests/unit/test_a.py", "tests/unit/test_b.py"])
    except (ValidationError, TypeError):
        pytest.fail("RunTestsInput should accept path as list[str]")
    assert inp.path == ["tests/unit/test_a.py", "tests/unit/test_b.py"]


def test_scope_full_field_exists_and_is_accepted():
    """RunTestsInput must accept scope='full' without ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    try:
        inp = RunTestsInput(scope="full")
    except (ValidationError, TypeError):
        pytest.fail("RunTestsInput should accept scope='full'")
    assert inp.scope == "full"  # type: ignore[attr-defined]


def test_no_path_no_scope_raises_validation_error():
    """RunTestsInput() without path or scope must raise ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        RunTestsInput()


def test_path_and_scope_mutual_exclusion_raises_validation_error():
    """Providing both path and scope must raise ValidationError."""
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        RunTestsInput(path="tests/unit.py", scope="full")


@pytest.mark.asyncio
async def test_path_list_produces_multiple_args_in_cmd(mock_run_pytest_sync, mock_settings):
    """path=['a.py', 'b.py'] must result in both paths as separate cmd args."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("2 passed in 0.20s\n", "", 0)

    await tool.execute(RunTestsInput(path=["tests/test_a.py", "tests/test_b.py"]))

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "tests/test_a.py" in cmd
    assert "tests/test_b.py" in cmd


@pytest.mark.asyncio
async def test_scope_full_produces_no_path_args_in_cmd(mock_run_pytest_sync, mock_settings):
    """scope='full' must run pytest without any explicit path arguments."""
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("10 passed in 1.00s\n", "", 0)

    await tool.execute(RunTestsInput(scope="full"))

    cmd = mock_run_pytest_sync.call_args[0][0]
    # cmd should not contain any test path arguments (only flags/options)
    path_like = [arg for arg in cmd if not arg.startswith("-") and arg not in (cmd[0], cmd[1], cmd[2])]
    assert path_like == [], f"Expected no path args for scope='full', got: {path_like}"
