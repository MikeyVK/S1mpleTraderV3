# tests/unit/mcp_server/validation/test_template_validator.py
"""
Unit tests for TemplateValidator.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from unittest.mock import patch

# Third-party
import pytest

# Module under test
from mcp_server.validation.template_validator import TemplateValidator


class TestTemplateValidator:
    """Test suite for TemplateValidator."""

    @pytest.fixture
    def validator(self) -> TemplateValidator:
        """Fixture for generic TemplateValidator (worker)."""
        return TemplateValidator("worker")

    def test_init_invalid_type(self) -> None:
        """Test initialization with invalid template type."""
        with pytest.raises(ValueError, match="Unknown template type: invalid"):
            TemplateValidator("invalid")

    def test_repr(self, validator: TemplateValidator) -> None:
        """Test string representation."""
        assert str(validator) == "TemplateValidator(type=worker)"

    @pytest.mark.asyncio
    async def test_validate_content_read_error(self, validator: TemplateValidator) -> None:
        """Test handling of file read errors."""
        with patch("pathlib.Path.read_text", side_effect=OSError("File not found")):
            result = await validator.validate("nonexistent.py")
            assert result.passed is False
            assert "Failed to read file" in result.issues[0].message

    @pytest.mark.asyncio
    async def test_validate_worker_valid(self, validator: TemplateValidator) -> None:
        """Test validation of a valid worker component."""
        content = """
        import typing
        from mcp_server.interface import BaseWorker, TaskResult
        
        class MyWorker(BaseWorker):
            async def execute(self, **kwargs) -> TaskResult:
                pass
        """
        result = await validator.validate("my_worker.py", content)
        assert result.passed is True
        assert not result.issues

    @pytest.mark.asyncio
    async def test_validate_worker_invalid_class_name(self, validator: TemplateValidator) -> None:
        """Test validation failure for missing class suffix."""
        content = """
        class MyComponent:
            def execute(self): pass
        """
        result = await validator.validate("worker.py", content)
        assert any("Missing class with suffix 'Worker'" in i.message for i in result.issues)

    @pytest.mark.asyncio
    async def test_validate_worker_missing_method(self, validator: TemplateValidator) -> None:
        """Test validation failure for missing required method."""
        content = """
        class MyWorker:
            pass
        """
        result = await validator.validate("worker.py", content)
        assert any("Missing required method: 'execute'" in i.message for i in result.issues)

    @pytest.mark.asyncio
    async def test_validate_tool_attributes(self) -> None:
        """Test validation of Tool required attributes."""
        val = TemplateValidator("tool")

        # Valid: Attributes defined as assignments
        content_valid = """
        class MyTool:
            name = "my_tool"
            description = "desc"
            input_schema = {}
            def execute(self): pass
        """
        result = await val.validate("tool.py", content_valid)
        assert result.passed is True

        # Valid: Attributes defined as properties
        content_props = """
        class MyTool:
            @property
            def name(self): return "tool"
            def description(self): pass
            def input_schema(self): pass
            def execute(self): pass
        """
        result_props = await val.validate("tool.py", content_props)
        assert result_props.passed is True

        # Invalid: Missing attributes
        content_invalid = """
        class MyTool:
            name = "tool"
        """
        result_inv = await val.validate("tool.py", content_invalid)
        messages = [i.message for i in result_inv.issues]
        assert any("Missing required attribute: 'description'" in m for m in messages)
        assert any("Missing required attribute: 'input_schema'" in m for m in messages)

    @pytest.mark.asyncio
    async def test_validate_imports_and_decorators(self) -> None:
        """Test validation of imports and decorators (DTO scenario)."""
        val = TemplateValidator("dto")

        # Valid
        content_valid = """
        from dataclasses import dataclass
        
        @dataclass
        class MyDTO:
            pass
        """
        result = await val.validate("dto.py", content_valid)
        assert result.passed is True

        # Invalid
        content_invalid = """
        class MyDTO:
            pass
        """
        result_inv = await val.validate("dto.py", content_invalid)
        assert any(
            "Missing required decorator: '@dataclass'" in i.message
            for i in result_inv.issues
        )
