"""Result types for scaffolding operations."""
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from mcp_server.scaffolding.utils import validate_pascal_case

if TYPE_CHECKING:
    from mcp_server.scaffolding.renderer import JinjaRenderer


@dataclass(frozen=True)
class ScaffoldResult:
    """Result of a scaffold operation."""
    content: str
    file_name: str | None = None


class BaseScaffolder:
    """Base implementation for scaffolders."""

    def __init__(self, renderer: "JinjaRenderer") -> None:
        """Initialize the scaffolder.

        Args:
            renderer: Template renderer instance
        """
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:  # noqa: ANN401
        """Validate scaffolding arguments.

        Args:
            **kwargs: Arguments to validate

        Returns:
            True if valid
        """
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True


class ComponentScaffolder(Protocol):
    """Protocol for component scaffolders."""

    def validate(self, **kwargs: Any) -> bool:  # noqa: ANN401
        """Validate scaffolding arguments."""

    def scaffold(self, name: str, **kwargs: Any) -> str:  # noqa: ANN401
        """Scaffold a component."""
