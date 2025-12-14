"""Schema Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class SchemaScaffolder(BaseScaffolder):
    """Scaffolds Pydantic Schemas."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Schema.

        Args:
            name: Schema root name
            **kwargs: Schema arguments

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        return str(self.renderer.render(
            "components/schema.py.jinja2",
            name=name,
            **kwargs
        ))
