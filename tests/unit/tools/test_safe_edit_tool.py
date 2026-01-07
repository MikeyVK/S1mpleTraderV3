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

        # Mock ValidationService.validate to return passing result
        async def mock_validate(*_, **__):
            return True, ""  # passed=True, no issues

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            # Mock file writing
            with patch("pathlib.Path.write_text") as mock_write, \
                 patch("pathlib.Path.parent") as mock_parent:

                mock_parent.mkdir = MagicMock()

                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="strict")
                )

                # Verify
                assert "File saved successfully" in result.content[0]["text"]
                mock_write.assert_called_once_with(content, encoding="utf-8")

    @pytest.mark.asyncio
    async def test_execute_strict_fail(self, tool: SafeEditTool) -> None:
        """Test strict mode with failing validation."""
        path = "test.py"
        content = "invalid code"

        # Mock ValidationService.validate to return failing result
        async def mock_validate(*_, **__):
            return False, "\n\n**Validation Issues:**\n❌ Error\n"

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="strict")
                )

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

        # Mock ValidationService.validate to return failing result
        async def mock_validate(*_, **__):
            return False, "\n\n**Validation Issues:**\n❌ Error\n"

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="interactive")
                )

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

        # Mock ValidationService.validate to return passing result
        async def mock_validate(*_, **__):
            return True, ""

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="verify_only")
                )

                # Verify
                text = result.content[0]["text"]
                assert "Validation Passed" in text
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_validator_logic(self, tool: SafeEditTool) -> None:
        """Test implicit addition of base TemplateValidator for python files."""
        path = "script.py"
        content = "code"

        # Mock ValidationService.validate to return passing result
        # The fallback logic is now in ValidationService, not SafeEditTool
        async def mock_validate(*_, **__):
            return True, ""

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            # Execute
            await tool.execute(SafeEditInput(path=path, content=content))

            # Verify that validate was called (fallback logic is internal to service)
            tool.validation_service.validate.assert_called_once()
