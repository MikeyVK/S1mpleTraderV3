"""Unit tests for code_tools.py."""
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mcp_server.tools.code_tools import CreateFileInput, CreateFileTool


@pytest.fixture
def mock_settings():
    with patch("mcp_server.tools.code_tools.settings") as mock:
        mock.server.workspace_root = "/workspace"
        yield mock

@pytest.mark.asyncio
async def test_create_file_tool_success(mock_settings):
    tool = CreateFileTool()
    params = CreateFileInput(path="test.txt", content="hello")

    with patch("builtins.open", mock_open()) as mock_file:
        with patch("pathlib.Path.mkdir"):
            # Mock resolve to simulate being inside workspace
            with patch("pathlib.Path.resolve") as mock_resolve:
                # Create specific mocks to track
                path_mock = MagicMock()
                path_mock.__str__.return_value = "/workspace/test.txt"
                # Mock the parent property for mkdir
                path_mock.parent = MagicMock()

                workspace_mock = MagicMock()
                workspace_mock.__str__.return_value = "/workspace"

                mock_resolve.side_effect = [path_mock, workspace_mock]

                result = await tool.execute(params)

                assert "File created: test.txt" in result.content[0]["text"]
                # Assert called with the SPECIFIC mock object
                mock_file.assert_called_with(path_mock, "w", encoding="utf-8")
                mock_file().write.assert_called_with("hello")

@pytest.mark.asyncio
async def test_create_file_tool_security_error(mock_settings):
    tool = CreateFileTool()
    params = CreateFileInput(path="../outside.txt", content="bad")

    with patch("pathlib.Path.resolve") as mock_resolve:
        mock_resolve.side_effect = [
            MagicMock(__str__=lambda x: "/outside.txt"), # full_path
            MagicMock(__str__=lambda x: "/workspace")    # workspace
        ]

        result = await tool.execute(params)

        assert result.is_error
        assert "Access denied" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_create_file_tool_deprecation_warning():
    tool = CreateFileTool()
    params = CreateFileInput(path="test.txt", content="hello")

    # We just want to check it warns, we can mock the rest to fail or succeed
    with patch("builtins.open", mock_open()):
        with patch("pathlib.Path.resolve", return_value=MagicMock(__str__=lambda x: "/workspace/test.txt")):
            with patch("mcp_server.tools.code_tools.settings"):
                with pytest.warns(DeprecationWarning, match="create_file is deprecated"):
                    try:
                        await tool.execute(params)
                    except Exception:
                        pass # Ignore execution errors, just check warning
