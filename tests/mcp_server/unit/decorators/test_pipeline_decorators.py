# c:\temp\pgmcp\tests\mcp_server\unit\decorators\test_pipeline_decorators.py
# template=unit_test version=3d15d309 created=2026-06-19T22:03Z updated=
"""
Unit tests for mcp_server.core.decorators.

Unit tests for Russian Doll pipeline decorators

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.core.decorators, unittest.mock]
@responsibilities:
    - Test TestPipelineDecorators functionality
    - Verify that ToolErrorHandlerDecorator, InputValidationDecorator,
      and EnforcementDecorator operate correctly
"""

# Standard library
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Third-party
import pytest
from pydantic import BaseModel, ConfigDict

from mcp_server.core.decorators import (
    EnforcementDecorator,
    InputValidationDecorator,
    ToolErrorHandlerDecorator,
)
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.exceptions import ValidationError as EnforcementValidationError
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.interfaces.itool import ITool

# Project modules
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import EnforcementRunner
from mcp_server.schemas.error_outputs import (
    ConfigErrorOutput,
    EnforcementErrorOutput,
    ExecutionErrorOutput,
    ValidationErrorOutput,
)


# Dummy models for testing
class DummyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int
    name: str = "test"


class DummyOutput(BaseModel):
    result: str


class TestPipelineDecorators:
    """Test suite for pipeline decorators."""

    @pytest.mark.asyncio
    async def test_tool_error_handler_decorator_success(self) -> None:
        """ErrorHandler should forward parameters and return success result."""
        mock_inner = AsyncMock(spec=ITool)
        mock_inner.name = "dummy"
        mock_inner.description = "desc"
        mock_inner.args_model = DummyInput

        expected_output = DummyOutput(result="ok")
        mock_inner.execute.return_value = expected_output

        decorator = ToolErrorHandlerDecorator(mock_inner)
        assert decorator.name == "dummy"
        assert decorator.description == "desc"
        assert decorator.args_model == DummyInput

        context = NoteContext()
        result = await decorator.execute({"value": 42}, context)
        assert result == expected_output
        mock_inner.execute.assert_awaited_once_with({"value": 42}, context)

    @pytest.mark.asyncio
    async def test_tool_error_handler_decorator_config_error(self) -> None:
        """ErrorHandler should catch ConfigError and return ConfigErrorOutput."""
        mock_inner = AsyncMock(spec=ITool)
        mock_inner.name = "dummy"
        mock_inner.execute.side_effect = ConfigError("Config is broken", file_path="config.yaml")

        decorator = ToolErrorHandlerDecorator(mock_inner)
        context = NoteContext()
        result = await decorator.execute({"value": 42}, context)

        assert isinstance(result, ConfigErrorOutput)
        assert result.success is False
        assert result.error_type == "ConfigError"
        assert result.error_message is not None
        assert "Config is broken" in result.error_message
        assert result.file_path == "config.yaml"

    @pytest.mark.asyncio
    async def test_tool_error_handler_decorator_generic_exception(self) -> None:
        """ErrorHandler should catch generic Exception, log it, and return ExecutionErrorOutput."""
        mock_inner = AsyncMock(spec=ITool)
        mock_inner.name = "dummy"
        mock_inner.execute.side_effect = ValueError("Something failed")

        decorator = ToolErrorHandlerDecorator(mock_inner)
        context = NoteContext()
        result = await decorator.execute({"value": 42}, context)

        assert isinstance(result, ExecutionErrorOutput)
        assert result.success is False
        assert result.error_type == "ExecutionError"
        assert result.error_message is not None
        assert "ValueError" in result.error_message
        assert "Something failed" in result.error_message
        assert result.traceback is not None
        assert result.params == {"value": 42}

    @pytest.mark.asyncio
    async def test_input_validation_decorator_success(self) -> None:
        """InputValidation should validate raw dict to BaseModel and call inner tool."""
        mock_inner = AsyncMock(spec=ICoreTool)
        mock_inner.name = "dummy"
        mock_inner.description = "desc"
        mock_inner.args_model = DummyInput

        expected_output = DummyOutput(result="ok")
        mock_inner.execute.return_value = expected_output

        decorator = InputValidationDecorator(mock_inner)
        assert decorator.name == "dummy"
        assert decorator.description == "desc"
        assert decorator.args_model == DummyInput

        context = NoteContext()
        result = await decorator.execute({"value": 42, "name": "validated"}, context)
        assert result == expected_output

        # Verify it passed a DummyInput model to inner tool
        args, _ = mock_inner.execute.call_args
        assert isinstance(args[0], DummyInput)
        assert args[0].value == 42
        assert args[0].name == "validated"

    @pytest.mark.asyncio
    async def test_input_validation_decorator_validation_error(self) -> None:
        """InputValidation should return ValidationErrorOutput on invalid input parameters."""
        mock_inner = AsyncMock(spec=ICoreTool)
        mock_inner.name = "dummy"
        mock_inner.args_model = DummyInput

        decorator = InputValidationDecorator(mock_inner)
        context = NoteContext()
        # "value" is missing and "extra_field" is forbidden
        result = await decorator.execute({"extra_field": "forbidden"}, context)

        assert isinstance(result, ValidationErrorOutput)
        assert result.success is False
        assert result.error_type == "ValidationError"
        assert result.error_message is not None
        assert "Invalid input for dummy" in result.error_message
        assert len(result.validation_errors) > 0
        assert result.params == {"extra_field": "forbidden"}

    @pytest.mark.asyncio
    async def test_input_validation_decorator_no_args_model(self) -> None:
        """InputValidation should bypass validation if args_model is None."""
        mock_inner = AsyncMock(spec=ICoreTool)
        mock_inner.name = "dummy"
        mock_inner.args_model = None

        expected_output = DummyOutput(result="ok")
        mock_inner.execute.return_value = expected_output

        decorator = InputValidationDecorator(mock_inner)
        context = NoteContext()
        result = await decorator.execute({}, context)
        assert result == expected_output
        mock_inner.execute.assert_awaited_once_with(None, context)

    @pytest.mark.asyncio
    async def test_enforcement_decorator_success(self) -> None:
        """EnforcementDecorator should run pre and post checks successfully."""
        mock_inner = AsyncMock(spec=ICoreTool)
        mock_inner.name = "dummy"
        mock_inner.description = "desc"
        mock_inner.args_model = DummyInput
        mock_inner.tool_category = "test_category"

        expected_output = DummyOutput(result="ok")
        mock_inner.execute.return_value = expected_output

        mock_runner = MagicMock(spec=EnforcementRunner)
        workspace = Path("/workspace")

        decorator = EnforcementDecorator(mock_inner, mock_runner, workspace)
        assert decorator.name == "dummy"
        assert decorator.description == "desc"
        assert decorator.args_model == DummyInput
        assert decorator.tool_category == "test_category"

        context = NoteContext()
        params = DummyInput(value=42)
        result = await decorator.execute(params, context)
        assert result == expected_output

        # Verify pre and post checks were run
        assert mock_runner.run.call_count == 2

        # Let's inspect call args more specifically
        calls = mock_runner.run.call_args_list
        assert calls[0][1]["timing"] == "pre"
        assert calls[0][1]["enforcement_ctx"].tool_name == "dummy"
        assert calls[0][1]["enforcement_ctx"].params == params

        assert calls[1][1]["timing"] == "post"
        assert calls[1][1]["enforcement_ctx"].tool_name == "dummy"

    @pytest.mark.asyncio
    async def test_enforcement_decorator_pre_validation_error(self) -> None:
        """EnforcementDecorator should return EnforcementErrorOutput and
        abort execution if pre check fails.
        """
        mock_inner = AsyncMock(spec=ICoreTool)
        mock_inner.name = "dummy"
        mock_inner.tool_category = "cat"

        mock_runner = MagicMock(spec=EnforcementRunner)
        mock_runner.run.side_effect = EnforcementValidationError(
            "Pre-check failed", error_code="ERR_PRE", params={"extra": "info"}
        )

        decorator = EnforcementDecorator(mock_inner, mock_runner, Path("/workspace"))
        context = NoteContext()
        params = DummyInput(value=42)
        result = await decorator.execute(params, context)

        assert isinstance(result, EnforcementErrorOutput)
        assert result.success is False
        assert result.error_type == "EnforcementError"
        assert result.error_code == "ERR_PRE"
        assert result.params == {"extra": "info"}

        # Inner tool execution should be skipped
        mock_inner.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_enforcement_decorator_post_validation_error(self) -> None:
        """EnforcementDecorator should return EnforcementErrorOutput if post check fails."""
        mock_inner = AsyncMock(spec=ICoreTool)
        mock_inner.name = "dummy"
        mock_inner.tool_category = "cat"
        mock_inner.execute.return_value = DummyOutput(result="ok")

        mock_runner = MagicMock(spec=EnforcementRunner)

        # Succeed on pre, fail on post
        def side_effect(event, timing, tool_category, enforcement_ctx, note_context):
            if timing == "post":
                raise EnforcementValidationError(
                    "Post-check failed", error_code="ERR_POST", params={"extra": "post"}
                )

        mock_runner.run.side_effect = side_effect

        decorator = EnforcementDecorator(mock_inner, mock_runner, Path("/workspace"))
        context = NoteContext()
        params = DummyInput(value=42)
        result = await decorator.execute(params, context)

        assert isinstance(result, EnforcementErrorOutput)
        assert result.success is False
        assert result.error_type == "EnforcementError"
        assert result.error_code == "ERR_POST"
        assert result.params == {"extra": "post"}

        mock_inner.execute.assert_awaited_once_with(params, context)
