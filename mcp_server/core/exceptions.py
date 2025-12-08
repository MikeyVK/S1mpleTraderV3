"""Core exceptions for the MCP server."""
from typing import Optional


class MCPError(Exception):
    """Base class for all MCP server exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "ERR_INTERNAL",
        hints: Optional[list[str]] = None
    ) -> None:
        """Initialize the MCP error."""
        super().__init__(message)
        self.message = message
        self.code = code
        self.hints = hints or []


class ValidationError(MCPError):
    """Raised when input validation fails."""

    def __init__(self, message: str, hints: Optional[list[str]] = None) -> None:
        """Initialize the validation error."""
        super().__init__(message, code="ERR_VALIDATION", hints=hints)


class PreflightError(MCPError):
    """Raised when pre-flight checks fail."""

    def __init__(self, message: str, blockers: Optional[list[str]] = None) -> None:
        """Initialize the preflight error."""
        super().__init__(message, code="ERR_PREFLIGHT", hints=blockers)
        self.blockers = blockers or []


class ExecutionError(MCPError):
    """Raised when tool execution fails."""

    def __init__(self, message: str, recovery: Optional[list[str]] = None) -> None:
        """Initialize the execution error."""
        super().__init__(message, code="ERR_EXECUTION", hints=recovery)
        self.recovery = recovery or []


class MCPSystemError(MCPError):
    """Raised when system/infrastructure fails."""

    def __init__(self, message: str, fallback: Optional[str] = None) -> None:
        """Initialize the system error."""
        super().__init__(message, code="ERR_SYSTEM")
        self.fallback = fallback
