"""Schema Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class SchemaScaffolder(BaseScaffolder):
    """Scaffolds Pydantic Schemas."""

    def scaffold(self, name: str, **kwargs: Any) -> str:  # noqa: ANN401
        """Scaffold a Schema.

        Args:
            name: Schema root name
            **kwargs: Schema arguments

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        try:
            return str(self.renderer.render(
                "components/schema.py.jinja2",
                name=name,
                **kwargs
            ))
        except Exception as e:
            # Fallback to generic component template
            if "not found" in str(e).lower():
                return str(self.renderer.render(
                    "components/generic.py.jinja2",
                    name=name,
                    **kwargs
                ))
            raise
