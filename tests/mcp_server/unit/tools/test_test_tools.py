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
    mock_run_pytest_sync.return_value = ("Test Output", "", 0)

    result = await tool.execute(RunTestsInput(path="tests/unit", verbose=False))

    assert "Test Output" in result.content[0]["text"]
    assert "✅ Tests passed" in result.content[0]["text"]

    # Verify call args
    call_args = mock_run_pytest_sync.call_args
    assert call_args is not None
    cmd = call_args[0][0]
    assert "pytest" in cmd[2] or "pytest" in cmd[1]  # Depending on if run as module
    assert "tests/unit" in cmd


@pytest.mark.asyncio
async def test_run_tests_failure(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("Tests Failed", "Error info", 1)

    result = await tool.execute(RunTestsInput(path="tests/foo.py"))

    assert "Tests Failed" in result.content[0]["text"]
    assert "Error info" in result.content[0]["text"]
    assert "❌ Tests failed" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_run_tests_markers(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()
    mock_run_pytest_sync.return_value = ("", "", 0)

    await tool.execute(RunTestsInput(markers="integration"))

    cmd = mock_run_pytest_sync.call_args[0][0]
    assert "-m" in cmd
    assert "integration" in cmd


@pytest.mark.asyncio
async def test_run_tests_exception(mock_run_pytest_sync, mock_settings):
    tool = RunTestsTool()
    mock_run_pytest_sync.side_effect = OSError("Boom")

    result = await tool.execute(RunTestsInput())

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
