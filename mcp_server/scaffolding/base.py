"""Result types for scaffolding operations."""
from dataclasses import dataclass
from typing import Protocol, Any


@dataclass(frozen=True)
class ScaffoldResult:
    """Result of a scaffold operation."""
    content: str
    file_name: str | None = None


class ComponentScaffolder(Protocol):
    """Protocol for component scaffolders."""

    def validate(self, **kwargs: Any) -> bool:
        """Validate scaffolding arguments.

        Args:
            **kwargs: Arguments to validate

        Returns:
            True if valid
        """

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a component.

        Args:
            name: Component name
            **kwargs: Component specific arguments

        Returns:
            Rendered code string
        """
