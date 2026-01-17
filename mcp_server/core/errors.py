"""Core error types for MCP server.

Contains configuration and validation error definitions.
"""

from typing import Optional


class ConfigError(Exception):
    """Configuration loading or validation error."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        """Initialize ConfigError.
        
        Args:
            message: Error message describing the problem
            file_path: Optional path to config file with error
        """
        self.message = message
        self.file_path = file_path
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with file context."""
        if self.file_path:
            return f"{self.message}\nFile: {self.file_path}"
        return self.message


class ValidationError(Exception):
    """Validation error for scaffolding operations.
    
    Raised when required fields are missing or invalid during
    artifact scaffolding validation.
    """
    
    def __init__(self, message: str, hints: list[str] | None = None):
        """Initialize ValidationError.
        
        Args:
            message: Error message describing validation failure
            hints: Optional list of suggestions to fix the error
        """
        self.message = message
        self.hints = hints or []
        super().__init__(message)
