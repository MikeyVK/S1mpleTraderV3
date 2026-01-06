"""Unit tests for test_tools.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_server.core.exceptions import ExecutionError
from mcp_server.tools.test_tools import RunTestsTool, RunTestsInput
from mcp_server.tools.tool_result import ToolResult

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
    assert "pytest" in cmd[2] or "pytest" in cmd[1] # Depending on if run as module
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
