"""DTO Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class DTOScaffolder(BaseScaffolder):
    """Scaffolds Data Transfer Objects."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a DTO.

        Args:
            name: DTO class name
            **kwargs: DTO specific arguments:
                - fields: list[dict]
                - docstring: str
                - ...

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        # Derive id_prefix if needed
        id_prefix = kwargs.get("id_prefix")
        if not id_prefix:
            clean_name = name.replace("DTO", "").replace("Plan", "")
            id_prefix = clean_name[:3].upper()
            kwargs["id_prefix"] = id_prefix

        # Enhance docstring default
        if not kwargs.get("docstring"):
            kwargs["docstring"] = f"{name} data transfer object."

        try:
            return str(self.renderer.render("components/dto.py.jinja2", name=name, **kwargs))
        except Exception as e:
            # Fallback to generic component template
            if "not found" in str(e).lower():
                return str(self.renderer.render("components/generic.py.jinja2", name=name, **kwargs))
            raise
