"""Tests for Validation tools."""

from unittest.mock import patch

import pytest

from mcp_server.tools.validation_tools import (
    ValidateDTOInput,
    ValidateDTOTool,
    ValidationInput,
    ValidationTool,
)


@pytest.mark.asyncio
async def test_validation_tool() -> None:
    """Test ValidationTool returns pass status for architecture validation."""
    tool = ValidationTool()
    result = await tool.execute(ValidationInput(scope="dtos"))
    assert "Architecture validation passed" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_dto_validation_tool() -> None:
    """Test ValidateDTOTool returns pass status for DTO validation."""
    tool = ValidateDTOTool()

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.read_text", return_value="@dataclass\nclass TestDTO: ..."):
            result = await tool.execute(ValidateDTOInput(file_path="backend/dtos/test.py"))

    assert result.is_error is False
    assert "DTO validation passed" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_dto_validation_tool_missing_file() -> None:
    """Test ValidateDTOTool returns ToolResult.error for missing files."""
    tool = ValidateDTOTool()

    with patch("pathlib.Path.exists", return_value=False):
        result = await tool.execute(ValidateDTOInput(file_path="this/file/does/not/exist.py"))

    assert result.is_error is True
    assert "DTO file not found" in result.content[0]["text"]
