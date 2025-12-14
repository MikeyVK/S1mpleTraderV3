"""Adapter Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class AdapterScaffolder(BaseScaffolder):
    """Scaffolds Adapters."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold an Adapter.

        Args:
            name: Adapter name
            **kwargs: Adapter args (methods, etc.)

        Returns:
            Rendered Python code
        """
        self.validate(name=name)
        adapter_name = name if name.endswith("Adapter") else f"{name}Adapter"

        return str(self.renderer.render(
            "components/adapter.py.jinja2",
            name=adapter_name,
            **kwargs
        ))
