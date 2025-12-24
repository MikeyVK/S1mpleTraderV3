# tests/unit/mcp_server/tools/test_template_validation_tool.py
"""
Unit tests for Template Validation Tool.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.template_validation_tool]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Module under test
from mcp_server.tools.template_validation_tool import (
    TemplateValidationTool,
    TemplateValidationInput
)
from mcp_server.validation.template_validator import TemplateValidator


class TestTemplateValidationTool:
    """Test suite for TemplateValidationTool."""

    @pytest.fixture
    def tool(self) -> TemplateValidationTool:
        """Fixture for TemplateValidationTool."""
        return TemplateValidationTool()

    @pytest.mark.asyncio
    async def test_execute_success(self, tool: TemplateValidationTool) -> None:
        """Test successful execution."""
        input_data = TemplateValidationInput(path="path/to/file.py", template_type="tool")

        with patch("mcp_server.tools.template_validation_tool.TemplateValidator") as mock_validator_cls:
            mock_validator = mock_validator_cls.return_value
            # validate returns ValidationResult object (or similar, assuming awaitable)
            mock_result = MagicMock()
            mock_result.passed = False
            i1 = MagicMock()
            i1.severity = "error"
            i1.message = "Issue 1"
            i2 = MagicMock()
            i2.severity = "warning"
            i2.message = "Issue 2"
            mock_result.issues = [i1, i2]

            # Since execute awaits validator.validate
            async def async_validate(path):
                return mock_result

            mock_validator.validate.side_effect = async_validate

            result = await tool.execute(input_data)

            assert "❌ Template Validation Failed" in result.content[0]["text"]
            assert "Issue 1" in result.content[0]["text"]
            assert "Issue 2" in result.content[0]["text"]
            mock_validator_cls.assert_called_with("tool")

    @pytest.mark.asyncio
    async def test_execute_no_issues(self, tool: TemplateValidationTool) -> None:
        """Test execution with no issues."""
        input_data = TemplateValidationInput(path="path/to/file.py", template_type="tool")

        with patch("mcp_server.tools.template_validation_tool.TemplateValidator") as mock_validator_cls:
            mock_validator = mock_validator_cls.return_value
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.issues = []

            async def async_validate(path):
                return mock_result
            mock_validator.validate.side_effect = async_validate

            result = await tool.execute(input_data)

            assert "✅ Template Validation Passed" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_error(self, tool: TemplateValidationTool) -> None:
        """Test execution error."""
        input_data = TemplateValidationInput(path="path/to/file.py", template_type="tool")

        with patch("mcp_server.tools.template_validation_tool.TemplateValidator") as mock_validator_cls:
            mock_validator = mock_validator_cls.return_value
            mock_validator.validate.side_effect = ValueError("Validation error")

            result = await tool.execute(input_data)

            assert "❌ Validation error: Validation error" in result.content[0]["text"]
