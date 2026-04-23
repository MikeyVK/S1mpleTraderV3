"""
Unit tests for mcp_server.core.error_handling.

C4 proof test: tool_error_handler without hints/blockers/recovery.
Proves that @tool_error_handler converts MCPError subclasses to ToolResult.error()
using only message, error_code, and file_path. No hints field exists on ToolResult after C4.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.core.error_handling, mcp_server.core.exceptions]
@responsibilities:
    - Test TestToolErrorHandlerC4 functionality
    - Verify C4 contract: no hints/blockers/recovery on exceptions or ToolResult
    - Verify exception constructors reject legacy kwargs
"""

# Third-party
import pytest

# Project modules
from mcp_server.core.error_handling import tool_error_handler
from mcp_server.core.exceptions import (
    ConfigError,
    ExecutionError,
    MCPError,
    PreflightError,
    ValidationError,
)
from mcp_server.tools.tool_result import ToolResult


class TestToolErrorHandlerC4:
    """C4: error handler produces ToolResult without hints field."""

    @pytest.mark.asyncio
    async def test_validation_error_no_hints_field(self) -> None:
        """ValidationError -> ToolResult with message and code, no hints."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise ValidationError("Field 'name' is required")

        result = await failing_tool()

        assert result.is_error
        assert result.error_code == "ERR_VALIDATION"
        assert "Field 'name' is required" in result.content[0]["text"]
        assert "hints" not in ToolResult.model_fields

    @pytest.mark.asyncio
    async def test_preflight_error_no_blockers_field(self) -> None:
        """PreflightError -> ToolResult with message and code, no blockers."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise PreflightError("Working directory is not clean")

        result = await failing_tool()

        assert result.is_error
        assert result.error_code == "ERR_PREFLIGHT"
        assert "not clean" in result.content[0]["text"]
        assert "hints" not in ToolResult.model_fields

    @pytest.mark.asyncio
    async def test_execution_error_no_recovery_field(self) -> None:
        """ExecutionError -> ToolResult with message and code, no recovery."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise ExecutionError("Git commit failed")

        result = await failing_tool()

        assert result.is_error
        assert result.error_code == "ERR_EXECUTION"
        assert "Git commit failed" in result.content[0]["text"]
        assert "hints" not in ToolResult.model_fields

    @pytest.mark.asyncio
    async def test_config_error_preserves_file_path(self) -> None:
        """ConfigError -> ToolResult with file_path, no hints."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise ConfigError("Invalid YAML", file_path=".st3/config/git.yaml")

        result = await failing_tool()

        assert result.is_error
        assert result.error_code == "ERR_CONFIG"
        assert result.file_path == ".st3/config/git.yaml"
        assert "Invalid YAML" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_mcp_error_base_class(self) -> None:
        """MCPError -> ToolResult with message and code."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise MCPError("Something went wrong", code="ERR_CUSTOM")

        result = await failing_tool()

        assert result.is_error
        assert result.error_code == "ERR_CUSTOM"
        assert "Something went wrong" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_value_error_handled(self) -> None:
        """ValueError -> ToolResult with 'Invalid input' prefix."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise ValueError("branch_type cannot be empty")

        result = await failing_tool()

        assert result.is_error
        assert "Invalid input" in result.content[0]["text"]
        assert "branch_type cannot be empty" in result.content[0]["text"]

    def test_tool_result_model_has_no_hints_field(self) -> None:
        """ToolResult Pydantic model must not have a hints field (C4 contract)."""
        fields = ToolResult.model_fields
        assert "hints" not in fields, "ToolResult must not have a hints field after C4"

    def test_exception_constructors_reject_hints_kwarg(self) -> None:
        """C4: exception constructors no longer accept hints/blockers/recovery."""
        with pytest.raises(TypeError):
            MCPError("test", hints=["should fail"])  # type: ignore[call-arg]

        with pytest.raises(TypeError):
            ValidationError("test", hints=["should fail"])  # type: ignore[call-arg]

        with pytest.raises(TypeError):
            PreflightError("test", blockers=["should fail"])  # type: ignore[call-arg]

        with pytest.raises(TypeError):
            ExecutionError("test", recovery=["should fail"])  # type: ignore[call-arg]
