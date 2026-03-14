"""Unit tests for code_tools.py."""

import contextlib
from collections.abc import Iterator
from unittest.mock import MagicMock, mock_open, patch

import pytest

from mcp_server.tools.code_tools import CreateFileInput, CreateFileTool


@pytest.fixture
def mock_settings() -> Iterator[MagicMock]:
    with patch("mcp_server.tools.code_tools.Settings") as mock:
        mock.from_env.return_value.server.workspace_root = "/workspace"
        yield mock


@pytest.mark.asyncio
async def test_create_file_tool_success(mock_settings: MagicMock) -> None:  # noqa: ARG001
    tool = CreateFileTool()
    params = CreateFileInput(path="test.txt", content="hello")

    with (
        patch("builtins.open", mock_open()) as mock_file,
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.resolve") as mock_resolve,
    ):
        # Mock resolve to simulate being inside workspace
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
async def test_create_file_tool_security_error(mock_settings: MagicMock) -> None:  # noqa: ARG001
    tool = CreateFileTool()
    params = CreateFileInput(path="../outside.txt", content="bad")

    with patch("pathlib.Path.resolve") as mock_resolve:
        mock_resolve.side_effect = [
            MagicMock(__str__=lambda _: "/outside.txt"),  # full_path
            MagicMock(__str__=lambda _: "/workspace"),  # workspace
        ]

        result = await tool.execute(params)

        assert result.is_error
        assert "Access denied" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_file_tool_deprecation_warning() -> None:
    tool = CreateFileTool()
    params = CreateFileInput(path="test.txt", content="hello")

    # We just want to check it warns, we can mock the rest to fail or succeed
    with (
        patch("builtins.open", mock_open()),
        patch(
            "pathlib.Path.resolve",
            return_value=MagicMock(__str__=lambda _: "/workspace/test.txt"),
        ),
        patch("mcp_server.tools.code_tools.Settings"),
        pytest.warns(DeprecationWarning, match="create_file is deprecated"),
        contextlib.suppress(Exception),
    ):
        await tool.execute(params)
