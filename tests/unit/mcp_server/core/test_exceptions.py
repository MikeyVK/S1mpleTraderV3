"""Tests for core exceptions."""
import pytest
from mcp_server.core.exceptions import (
    MCPError, ValidationError, PreflightError, ExecutionError, SystemError
)

def test_mcp_error_defaults():
    error = MCPError("Something went wrong")
    assert error.message == "Something went wrong"
    assert error.code == "ERR_INTERNAL"
    assert error.hints == []

def test_validation_error():
    error = ValidationError("Invalid input", hints=["Check format"])
    assert error.code == "ERR_VALIDATION"
    assert error.hints == ["Check format"]

def test_preflight_error():
    error = PreflightError("Check failed", blockers=["Dirty git tree"])
    assert error.code == "ERR_PREFLIGHT"
    assert error.blockers == ["Dirty git tree"]
    assert error.hints == ["Dirty git tree"]

def test_execution_error():
    error = ExecutionError("Command failed", recovery=["Try again"])
    assert error.code == "ERR_EXECUTION"
    assert error.recovery == ["Try again"]

def test_system_error():
    error = SystemError("Network down", fallback="Use cache")
    assert error.code == "ERR_SYSTEM"
    assert error.fallback == "Use cache"
