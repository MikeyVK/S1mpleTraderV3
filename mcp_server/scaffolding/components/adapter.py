"""Adapter Scaffolder Component."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError
from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import validate_pascal_case


class AdapterScaffolder(ComponentScaffolder):
    """Scaffolds Adapter classes."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize adapter scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate adapter arguments."""
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True

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

        try:
            return self.renderer.render(
                "components/adapter.py.jinja2",
                name=adapter_name,
                **kwargs
            )
        except ExecutionError:
            return self._render_fallback(adapter_name, **kwargs)

    def _render_fallback(self, name: str, **kwargs: Any) -> str:
        """Fallback rendering."""
        methods = kwargs.get("methods", [])

        lines = [
            '"""Generated Adapter module."""',
            "from typing import Any",
            "",
            "",
            f"class {name}:",
            f'    """{name} for external integration."""',
            "",
            "    def __init__(self) -> None:",
            '        """Initialize the adapter."""',
            "        pass",
            "",
        ]

        for method in methods:
            m_name = method.get("name", "unknown")
            m_params = method.get("params", "")
            m_return = method.get("return_type", "Any")
            lines.extend([
                f"    def {m_name}(self, {m_params}) -> {m_return}:",
                f'        """Execute {m_name} operation."""',
                "        raise NotImplementedError()",
                "",
            ])

        return "\n".join(lines)
