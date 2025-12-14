"""Resource Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import validate_pascal_case


class ResourceScaffolder(ComponentScaffolder):
    """Scaffolds Resource classes."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize resource scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate resource arguments."""
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Resource.

        Args:
            name: Resource name
            **kwargs: Resource args

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        return self.renderer.render(
            "components/resource.py.jinja2",
            name=name,
            **kwargs
        )
