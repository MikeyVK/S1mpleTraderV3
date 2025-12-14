"""Generic Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class GenericScaffolder(BaseScaffolder):
    """Scaffolds Generic Components from custom templates."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a generic component.

        Args:
            name: Component name
            **kwargs: Context variables. Must include 'template_name'.

        Returns:
            Rendered content
        """
        self.validate(name=name)

        template_name = kwargs.pop("template_name", None)
        if not template_name:
            raise ValueError("template_name is required for GenericScaffolder")

        return str(self.renderer.render(template_name, **kwargs))
