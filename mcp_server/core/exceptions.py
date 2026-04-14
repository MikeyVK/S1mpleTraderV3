"""
Core exceptions for the MCP server.

Base exception hierarchy for the entire MCP server.
Ensures consistent error handling across tools, managers, and adapters.

@layer: Core
@dependencies: [Standard Library]
@responsibilities:
    - Define base MCPError class
    - Define specific error types (ConfigError, ValidationError, etc.)
    - Provide standard error codes
"""

from typing import Any


class MCPError(Exception):
    """Base class for all MCP server exceptions."""

    def __init__(self, message: str, code: str = "ERR_INTERNAL") -> None:
        """Initialize the MCP error."""
        self.message = message
        self.code = code
        super().__init__(message)


class ConfigError(MCPError):
    """Configuration loading or validation error."""

    def __init__(self, message: str, file_path: str | None = None) -> None:
        """Initialize the configuration error.

        Args:
            message: Error message describing the problem
            file_path: Optional path to config file with error
        """
        formatted_message = message
        if file_path:
            formatted_message = f"{message}\nFile: {file_path}"

        super().__init__(formatted_message, code="ERR_CONFIG")
        self.file_path = file_path


class ValidationError(MCPError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        schema: Any = None,  # noqa: ANN401  # Core layer; TemplateSchema would violate layer deps
    ) -> None:
        """Initialize the validation error.

        Args:
            message: Error message describing the validation failure
            schema: Optional TemplateSchema with required/optional fields
        """
        super().__init__(message, code="ERR_VALIDATION")
        self.schema = schema
        self.missing: list[str] = []
        self.provided: list[str] = []

    def to_resource_dict(self, artifact_type: str) -> dict[str, Any]:
        """Generate structured resource data for ToolResult.

        Used by MCP tools to add resource content item with complete
        schema and validation details for agent consumption.

        Args:
            artifact_type: Artifact type identifier (e.g., "dto")

        Returns:
            Dict suitable for ToolResult resource content item
        """
        data: dict[str, Any] = {
            "artifact_type": artifact_type,
        }

        if self.schema:
            data["schema"] = self.schema.to_dict()

        if self.missing or self.provided:
            data["validation"] = {"missing": self.missing, "provided": self.provided}

        return data


class MetadataParseError(ValidationError):
    """Raised when scaffold metadata parsing fails.

    Subclass of ValidationError for metadata-specific validation errors.
    Used by ScaffoldMetadataParser when metadata format is invalid.
    """

    def __init__(self, message: str, file_path: str | None = None) -> None:
        """Initialize the metadata parse error.

        Args:
            message: Error message describing the parsing problem
            file_path: Optional path to file with invalid metadata
        """
        formatted_message = message
        if file_path:
            formatted_message = f"{message}\nFile: {file_path}"

        super().__init__(formatted_message)
        self.file_path = file_path


class PreflightError(MCPError):
    """Raised when pre-flight checks fail."""

    def __init__(self, message: str) -> None:
        """Initialize the preflight error."""
        super().__init__(message, code="ERR_PREFLIGHT")


class ExecutionError(MCPError):
    """Raised when tool execution fails."""

    def __init__(self, message: str) -> None:
        """Initialize the execution error."""
        super().__init__(message, code="ERR_EXECUTION")


class MCPSystemError(MCPError):
    """Raised when system/infrastructure fails."""

    def __init__(self, message: str, fallback: str | None = None) -> None:
        """Initialize the system error."""
        super().__init__(message, code="ERR_SYSTEM")
        self.fallback = fallback
