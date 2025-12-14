"""Resource Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class ResourceScaffolder(BaseScaffolder):
    """Scaffolds API Resources."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Resource.

        Args:
            name: Resource name
            **kwargs: Resource arguments

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        try:
            return str(self.renderer.render(
                "components/resource.py.jinja2",
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
