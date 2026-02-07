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

        try:
            return str(self.renderer.render(template_name, **kwargs))
        except Exception as e:
            # Fallback to generic template based on file type
            if "not found" in str(e).lower():
                # Determine fallback based on template extension
                if template_name.endswith(".py.jinja2"):
                    return str(self.renderer.render(
                        "components/generic.py.jinja2",
                        name=name,
                        **kwargs
                    ))
                if template_name.endswith(".md.jinja2"):
                    return str(self.renderer.render(
                        "documents/generic.md.jinja2",
                        name=name,
                        **kwargs
                    ))
            raise
