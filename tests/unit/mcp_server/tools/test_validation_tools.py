"""Tests for Validation tools."""
import pytest
from mcp_server.tools.validation_tools import ValidationTool, ValidateDTOTool

@pytest.mark.asyncio
async def test_validation_tool():
    tool = ValidationTool()
    result = await tool.execute(scope="dtos")
    assert "Architecture validation passed" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_dto_validation_tool():
    tool = ValidateDTOTool()
    result = await tool.execute(file_path="backend/dtos/test.py")
    assert "DTO validation passed" in result.content[0]["text"]
