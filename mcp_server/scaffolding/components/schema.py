"""Schema Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import validate_pascal_case


class SchemaScaffolder(ComponentScaffolder):
    """Scaffolds Schema (Pydantic models)."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize schema scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate schema arguments."""
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Schema.

        Args:
            name: Schema name
            **kwargs: Schema args

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        return self.renderer.render(
            "components/schema.py.jinja2",
            name=name,
            **kwargs
        )
