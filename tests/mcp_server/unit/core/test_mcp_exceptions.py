"""Tests for core exceptions."""

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
    assert error.hints == []


def test_validation_error() -> None:
    """Test ValidationError stores hints correctly."""
    error = ValidationError("Invalid input", hints=["Check format"])
    assert error.code == "ERR_VALIDATION"
    assert error.hints == ["Check format"]


def test_preflight_error() -> None:
    """Test PreflightError stores blockers as hints."""
    error = PreflightError("Check failed", blockers=["Dirty git tree"])
    assert error.code == "ERR_PREFLIGHT"
    assert error.blockers == ["Dirty git tree"]
    assert error.hints == ["Dirty git tree"]


def test_execution_error() -> None:
    """Test ExecutionError stores recovery steps."""
    error = ExecutionError("Command failed", recovery=["Try again"])
    assert error.code == "ERR_EXECUTION"
    assert error.recovery == ["Try again"]


def test_system_error() -> None:
    """Test MCPSystemError stores fallback action."""
    error = MCPSystemError("Network down", fallback="Use cache")
    assert error.code == "ERR_SYSTEM"
    assert error.fallback == "Use cache"
