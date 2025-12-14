"""Tool Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import validate_pascal_case


class ToolScaffolder(ComponentScaffolder):
    """Scaffolds Tool classes."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize tool scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate tool arguments."""
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Tool.

        Args:
            name: Tool name
            **kwargs: Tool args

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        tool_name = name if name.endswith("Tool") else f"{name}Tool"

        return self.renderer.render(
            "components/tool.py.jinja2",
            name=tool_name,
            **kwargs
        )
