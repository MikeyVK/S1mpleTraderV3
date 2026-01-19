"""
Core exceptions for the MCP server.

Base exception hierarchy for the entire MCP server.
Ensures consistent error handling across tools, managers, and adapters.

@layer: Core
@dependencies: [Standard Library]
@responsibilities:
    - Define base MCPError class
    - Define specific error types (ConfigError, ValidationError, etc.)
    - Provide standard error codes and hint structures
"""


class MCPError(Exception):
    """Base class for all MCP server exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "ERR_INTERNAL",
        hints: list[str] | None = None
    ) -> None:
        """Initialize the MCP error."""
        super().__init__(message)
        self.message = message
        self.code = code
        self.hints = hints or []


class ConfigError(MCPError):
    """Configuration loading or validation error."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        hints: list[str] | None = None
    ) -> None:
        """Initialize the configuration error.

        Args:
            message: Error message describing the problem
            file_path: Optional path to config file with error
            hints: Optional list of suggestions to fix the error
        """
        # Format message with file context if provided
        formatted_message = message
        if file_path:
            formatted_message = f"{message}\nFile: {file_path}"

        super().__init__(formatted_message, code="ERR_CONFIG", hints=hints)
        self.file_path = file_path


class ValidationError(MCPError):
    """Raised when input validation fails."""

    def __init__(self, message: str, hints: list[str] | None = None) -> None:
        """Initialize the validation error."""
        super().__init__(message, code="ERR_VALIDATION", hints=hints)


class PreflightError(MCPError):
    """Raised when pre-flight checks fail."""

    def __init__(self, message: str, blockers: list[str] | None = None) -> None:
        """Initialize the preflight error."""
        super().__init__(message, code="ERR_PREFLIGHT", hints=blockers)
        self.blockers = blockers or []


class ExecutionError(MCPError):
    """Raised when tool execution fails."""

    def __init__(self, message: str, recovery: list[str] | None = None) -> None:
        """Initialize the execution error."""
        super().__init__(message, code="ERR_EXECUTION", hints=recovery)
        self.recovery = recovery or []


class MCPSystemError(MCPError):
    """Raised when system/infrastructure fails."""

    def __init__(self, message: str, fallback: str | None = None) -> None:
        """Initialize the system error."""
        super().__init__(message, code="ERR_SYSTEM")
        self.fallback = fallback
