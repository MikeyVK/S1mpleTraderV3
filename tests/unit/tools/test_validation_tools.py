"""Tests for Validation tools."""
import pytest

from mcp_server.tools.validation_tools import (
    ValidateDTOTool, ValidateDTOInput,
    ValidationTool, ValidationInput
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
    result = await tool.execute(ValidateDTOInput(file_path="backend/dtos/test.py"))
    assert "DTO validation passed" in result.content[0]["text"]
