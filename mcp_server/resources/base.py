"""Base class for MCP resources."""
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseResource(ABC):
    """Abstract base class for all resources."""

    uri_pattern: str
    description: str = ""
    mime_type: str = "application/json"

    @abstractmethod
    async def read(self, uri: str) -> str:
        """Read the resource content."""
        pass

    def matches(self, uri: str) -> bool:
        """Check if the URI matches this resource's pattern."""
        # Simple exact match for now, could be regex later
        return uri == self.uri_pattern
