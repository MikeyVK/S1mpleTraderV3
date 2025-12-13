# tests/unit/mcp_server/tools/test_safe_edit_tool.py
"""
Unit tests for SafeEditTool.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Module under test
from pydantic import ValidationError
from mcp_server.tools.safe_edit_tool import SafeEditTool, SafeEditInput
from mcp_server.validation.base import ValidationResult, ValidationIssue


class TestSafeEditTool:
    """Test suite for SafeEditTool."""

    @pytest.fixture
    def tool(self) -> SafeEditTool:
        """Fixture for SafeEditTool."""
        return SafeEditTool()

    @pytest.mark.asyncio
    async def test_missing_arguments(self, tool: SafeEditTool) -> None:
        """Test execution with missing arguments."""
        # Missing content key raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(path="test.py")

        # Missing path key raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(content="code")

    @pytest.mark.asyncio
    async def test_execute_strict_pass(self, tool: SafeEditTool) -> None:
        """Test strict mode with passing validation."""
        path = "test.py"
        content = "valid code"

        with patch("mcp_server.tools.safe_edit_tool.ValidatorRegistry") as mock_registry:
            # Setup validator mock
            mock_validator = MagicMock()

            async def async_validate(*_, **__):
                return ValidationResult(passed=True, score=10.0, issues=[])
            mock_validator.validate.side_effect = async_validate

            mock_registry.get_validators.return_value = [mock_validator]

            # Mock file writing
            with patch("pathlib.Path.write_text") as mock_write, \
                 patch("pathlib.Path.parent") as mock_parent:

                mock_parent.mkdir = MagicMock()

                # Execute
                result = await tool.execute(SafeEditInput(path=path, content=content, mode="strict"))

                # Verify
                assert "File saved successfully" in result.content[0]["text"]
                mock_write.assert_called_once_with(content, encoding="utf-8")

    @pytest.mark.asyncio
    async def test_execute_strict_fail(self, tool: SafeEditTool) -> None:
        """Test strict mode with failing validation."""
        path = "test.py"
        content = "invalid code"

        with patch("mcp_server.tools.safe_edit_tool.ValidatorRegistry") as mock_registry:
            # Setup failing validator
            mock_validator = MagicMock()

            async def async_validate(*_, **__):
                return ValidationResult(
                    passed=False,
                    score=0.0,
                    issues=[ValidationIssue(message="Error", severity="error")]
                )
            mock_validator.validate.side_effect = async_validate
            mock_registry.get_validators.return_value = [mock_validator]

            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(SafeEditInput(path=path, content=content, mode="strict"))

                # Verify
                text = result.content[0]["text"]
                assert "Edit rejected" in text
                assert "Error" in text
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_interactive_fail(self, tool: SafeEditTool) -> None:
        """Test interactive mode allows saving even with validation failure."""
        path = "test.py"
        content = "invalid code"

        with patch("mcp_server.tools.safe_edit_tool.ValidatorRegistry") as mock_registry:
            # Setup failing validator
            mock_validator = MagicMock()

            async def async_validate(*_, **__):
                return ValidationResult(
                    passed=False,
                    score=0.0,
                    issues=[ValidationIssue(message="Error", severity="error")]
                )
            mock_validator.validate.side_effect = async_validate
            mock_registry.get_validators.return_value = [mock_validator]

            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(SafeEditInput(path=path, content=content, mode="interactive"))

                # Verify
                text = result.content[0]["text"]
                assert "File saved successfully" in text
                assert "Saved with validation warnings" in text
                mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_verify_only(self, tool: SafeEditTool) -> None:
        """Test verify_only mode does not write to file."""
        path = "test.py"
        content = "code"

        with patch("mcp_server.tools.safe_edit_tool.ValidatorRegistry") as mock_registry:
            # Setup passing validator
            mock_validator = MagicMock()

            async def async_validate(*_, **__):
                return ValidationResult(passed=True, score=10.0, issues=[])
            mock_validator.validate.side_effect = async_validate
            mock_registry.get_validators.return_value = [mock_validator]

            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(SafeEditInput(path=path, content=content, mode="verify_only"))

                # Verify
                text = result.content[0]["text"]
                assert "Validation Passed" in text
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_validator_logic(self, tool: SafeEditTool) -> None:
        """Test implicit addition of base TemplateValidator for python files."""
        path = "script.py"
        content = "code"

        with patch("mcp_server.tools.safe_edit_tool.ValidatorRegistry") as mock_registry:
            # Return empty list initially
            mock_registry.get_validators.return_value = []

            # Use side_effect to inspect the validators list passed to _validate
            # equivalent logic. Since _validate is internal, we can verify via behavior.
            # safe_edit_tool._validate loops over validators.
            # If we mock TemplateValidator("base") and it gets called, we know logic worked.

            with patch("mcp_server.tools.safe_edit_tool.TemplateValidator") as mock_tmpl_cls:
                # Setup base template validator mock
                mock_base_instance = MagicMock()

                async def async_validate(*_, **__):
                    return ValidationResult(passed=True, score=10.0, issues=[])
                mock_base_instance.validate.side_effect = async_validate
                mock_tmpl_cls.return_value = mock_base_instance

                # Execute
                await tool.execute(SafeEditInput(path=path, content=content))

                # Verify that TemplateValidator was instantiated with "base"
                mock_tmpl_cls.assert_called_with("base")
                # And its validate method was called
                mock_base_instance.validate.assert_called()
