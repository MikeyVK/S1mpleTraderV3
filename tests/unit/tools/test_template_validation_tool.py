# tests/unit/mcp_server/tools/test_template_validation_tool.py
"""
Unit tests for TemplateValidationTool.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from typing import Any
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Module under test
from pydantic import ValidationError
from mcp_server.tools.template_validation_tool import TemplateValidationTool, TemplateValidationInput
from mcp_server.validation.base import ValidationResult, ValidationIssue


class TestTemplateValidationTool:
    """Test suite for TemplateValidationTool."""

    @pytest.fixture
    def tool(self) -> TemplateValidationTool:
        """Fixture for TemplateValidationTool."""
        return TemplateValidationTool()

    @pytest.mark.asyncio
    async def test_missing_arguments(self, tool: TemplateValidationTool) -> None:
        """Test execution with missing arguments."""
        # Missing template_type
        with pytest.raises(ValidationError):
            TemplateValidationInput(path="test.py")

        # Missing path
        with pytest.raises(ValidationError):
            TemplateValidationInput(template_type="worker")

    @pytest.mark.asyncio
    async def test_execute_pass(self, tool: TemplateValidationTool) -> None:
        """Test successful validation execution."""
        path = "worker.py"
        template_type = "worker"
        target = "mcp_server.tools.template_validation_tool.TemplateValidator"

        with patch(target) as mock_validator_cls:
            # Setup mock instance
            mock_instance = MagicMock()

            async def async_validate(*_: Any, **__: Any) -> ValidationResult:
                return ValidationResult(passed=True, score=10.0, issues=[])

            mock_instance.validate.side_effect = async_validate
            mock_validator_cls.return_value = mock_instance

            # Execute
            result = await tool.execute(TemplateValidationInput(path=path, template_type=template_type))

            # Verify
            assert "Template Validation Passed" in result.content[0]["text"]
            mock_validator_cls.assert_called_with(template_type)
            mock_instance.validate.assert_called_with(path)

    @pytest.mark.asyncio
    async def test_execute_fail(self, tool: TemplateValidationTool) -> None:
        """Test failed validation flow with formatting check."""
        path = "worker.py"
        template_type = "worker"
        target = "mcp_server.tools.template_validation_tool.TemplateValidator"

        with patch(target) as mock_validator_cls:
            # Setup failing mock
            mock_instance = MagicMock()

            async def async_validate(*_: Any, **__: Any) -> ValidationResult:
                return ValidationResult(
                    passed=False,
                    score=0.0,
                    issues=[ValidationIssue(message="Missing method", severity="error")]
                )

            mock_instance.validate.side_effect = async_validate
            mock_validator_cls.return_value = mock_instance

            # Execute
            result = await tool.execute(TemplateValidationInput(path=path, template_type=template_type))

            # Verify
            text = result.content[0]["text"]
            assert "Template Validation Failed" in text
            assert "Missing method" in text
            assert "❌" in text

    @pytest.mark.asyncio
    async def test_execute_value_error(self, tool: TemplateValidationTool) -> None:
        """Test handling of invalid template type (ValueError)."""
        # Pydantic validation now catches this before execution
        with pytest.raises(ValidationError):
            TemplateValidationInput(path="test.py", template_type="invalid")

    @pytest.mark.asyncio
    async def test_execute_os_error(self, tool: TemplateValidationTool) -> None:
        """Test handling of file read error (OSError) from the validator."""
        path = "test.py"
        template_type = "worker"
        target = "mcp_server.tools.template_validation_tool.TemplateValidator"

        with patch(target) as mock_validator_cls:
            mock_instance = MagicMock()
            # Simulate validate method raising OSError
            mock_instance.validate.side_effect = OSError("Access denied")
            mock_validator_cls.return_value = mock_instance

            result = await tool.execute(TemplateValidationInput(path=path, template_type=template_type))

            assert "Validation error" in result.content[0]["text"]
            assert "Access denied" in result.content[0]["text"]
