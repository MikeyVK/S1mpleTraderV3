"""Tool Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class ToolScaffolder(BaseScaffolder):
    """Scaffolds MCP Tools."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Tool.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Rendered Python code
        """
        self.validate(name=name)
        tool_name = name if name.endswith("Tool") else f"{name}Tool"

        try:
            return str(self.renderer.render(
                "components/tool.py.jinja2",
                name=tool_name,
                **kwargs
            ))
        except Exception as e:
            # Fallback to generic component template
            if "not found" in str(e).lower():
                return str(self.renderer.render(
                    "components/generic.py.jinja2",
                    name=tool_name,
                    **kwargs
                ))
            raise
