"""Interface Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class InterfaceScaffolder(BaseScaffolder):
    """Scaffolds Interfaces (Protocols)."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold an Interface.

        Args:
            name: Interface name
            **kwargs: Context variables

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        return str(self.renderer.render(
            "components/interface.py.jinja2",
            name=name,
            **kwargs
        ))
