"""Tests for core exceptions.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.core.exceptions
"""

from mcp_server.core.exceptions import (
    ExecutionError,
    MCPError,
    MCPSystemError,
    PreflightError,
    ValidationError,
)


def test_mcp_error_defaults() -> None:
    """Test MCPError has correct default values."""
    error = MCPError("Something went wrong")
    assert error.message == "Something went wrong"
    assert error.code == "ERR_INTERNAL"


def test_validation_error() -> None:
    """Test ValidationError has correct code."""
    error = ValidationError("Invalid input")
    assert error.code == "ERR_VALIDATION"
    assert error.message == "Invalid input"


def test_preflight_error() -> None:
    """Test PreflightError has correct code."""
    error = PreflightError("Check failed")
    assert error.code == "ERR_PREFLIGHT"
    assert error.message == "Check failed"


def test_execution_error() -> None:
    """Test ExecutionError has correct code."""
    error = ExecutionError("Command failed")
    assert error.code == "ERR_EXECUTION"
    assert error.message == "Command failed"


def test_system_error() -> None:
    """Test MCPSystemError stores fallback action."""
    error = MCPSystemError("Network down", fallback="Use cache")
    assert error.code == "ERR_SYSTEM"
    assert error.fallback == "Use cache"
