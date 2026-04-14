"""
@module: tests.unit.core.test_exceptions
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.core.exceptions
@responsibilities:
  - Unit tests for exception hierarchy
  - Verify exception contracts (code, message)
  - Ensure ConfigError format includes file_path
"""

# Third-party
import pytest

# Project
from mcp_server.core.exceptions import (
    ConfigError,
    ExecutionError,
    MCPError,
    MCPSystemError,
    PreflightError,
    ValidationError,
)


def test_mcp_error_base_contract() -> None:
    """MCPError has message and code."""
    error = MCPError("Test error", code="ERR_TEST")

    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.code == "ERR_TEST"


def test_mcp_error_default_code() -> None:
    """MCPError defaults to ERR_INTERNAL."""
    error = MCPError("Internal error")

    assert error.code == "ERR_INTERNAL"


def test_config_error_with_file_path() -> None:
    """ConfigError formats message with file path."""
    error = ConfigError(
        "Invalid YAML syntax",
        file_path=".st3/artifacts.yaml",
    )

    assert "Invalid YAML syntax" in str(error)
    assert ".st3/artifacts.yaml" in str(error)
    assert error.code == "ERR_CONFIG"
    assert error.file_path == ".st3/artifacts.yaml"


def test_config_error_without_file_path() -> None:
    """ConfigError works without file_path."""
    error = ConfigError("Configuration missing")

    assert str(error) == "Configuration missing"
    assert error.file_path is None
    assert error.code == "ERR_CONFIG"


def test_validation_error() -> None:
    """ValidationError has ERR_VALIDATION code."""
    error = ValidationError("Missing required field: title")

    assert error.code == "ERR_VALIDATION"
    assert "Missing required field: title" in str(error)


def test_preflight_error() -> None:
    """PreflightError has ERR_PREFLIGHT code."""
    error = PreflightError("Pre-flight checks failed")

    assert error.code == "ERR_PREFLIGHT"
    assert "Pre-flight checks failed" in str(error)


def test_execution_error() -> None:
    """ExecutionError has ERR_EXECUTION code."""
    error = ExecutionError("Tool execution failed")

    assert error.code == "ERR_EXECUTION"
    assert "Tool execution failed" in str(error)


def test_system_error() -> None:
    """MCPSystemError has fallback."""
    error = MCPSystemError("Database connection failed", fallback="Use in-memory cache")

    assert error.code == "ERR_SYSTEM"
    assert error.fallback == "Use in-memory cache"


def test_exception_inheritance() -> None:
    """All exceptions inherit from MCPError."""
    assert issubclass(ConfigError, MCPError)
    assert issubclass(ValidationError, MCPError)
    assert issubclass(PreflightError, MCPError)
    assert issubclass(ExecutionError, MCPError)
    assert issubclass(MCPSystemError, MCPError)


def test_exception_catchable_as_base() -> None:
    """Exceptions can be caught as MCPError."""
    with pytest.raises(MCPError) as exc_info:
        raise ConfigError("Test error")

    assert isinstance(exc_info.value, ConfigError)
