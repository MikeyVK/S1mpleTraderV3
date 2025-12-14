"""DTO Scaffolder Component."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError
from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import validate_pascal_case


class DTOScaffolder(ComponentScaffolder):
    """Scaffolds Data Transfer Objects."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize the DTO scaffolder.

        Args:
            renderer: Template renderer instance
        """
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate DTO arguments.

        Args:
            **kwargs: DTO generation arguments (name, fields)

        Returns:
            True if valid
        """
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True

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
            return self.renderer.render("components/dto.py.jinja2", name=name, **kwargs)
        except ExecutionError:
            return self._render_fallback(name, **kwargs)

    def _render_fallback(self, name: str, **kwargs: Any) -> str:
        """Fallback rendering without template.

        Args:
            name: DTO name
            **kwargs: DTO args

        Returns:
            Rendered string
        """
        fields = kwargs.get("fields", [])
        docstring = kwargs.get("docstring")

        lines = [
            '"""Generated DTO module."""',
            "from dataclasses import dataclass",
            "from typing import Any",
            "",
            "",
            "@dataclass(frozen=True)",
            f"class {name}:",
            f'    """{docstring}"""',
            "",
        ]

        for field in fields:
            f_name = field.get("name")
            f_type = field.get("type", "Any")
            if "default" in field:
                lines.append(f"    {f_name}: {f_type} = {field['default']}")
            else:
                lines.append(f"    {f_name}: {f_type}")

        if not fields:
            lines.append("    pass")

        lines.append("")
        return "\n".join(lines)
