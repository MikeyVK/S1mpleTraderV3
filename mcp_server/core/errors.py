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
