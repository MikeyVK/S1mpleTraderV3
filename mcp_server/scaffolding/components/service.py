"""Service Scaffolder Component."""
from typing import Any

from mcp_server.scaffolding.base import BaseScaffolder


class ServiceScaffolder(BaseScaffolder):
    """Scaffolds Services."""

    def scaffold(self, name: str, **kwargs: Any) -> str:  # noqa: ANN401
        """Scaffold a Service.

        Args:
            name: Service name
            **kwargs: Service arguments (service_type, dependencies, etc.)

        Returns:
            Rendered Python code
        """
        self.validate(name=name)
        service_name = name if name.endswith("Service") else f"{name}Service"
        service_type = kwargs.get("service_type", "orchestrator")

        template_map = {
            "orchestrator": "components/service_orchestrator.py.jinja2",
            "command": "components/service_command.py.jinja2",
            "query": "components/service_query.py.jinja2",
        }

        template_path = template_map.get(service_type, template_map["orchestrator"])

        try:
            return str(self.renderer.render(
                template_path,
                name=service_name,
                **kwargs
            ))
        except Exception as e:
            # Fallback to generic component template
            if "not found" in str(e).lower():
                return str(self.renderer.render(
                    "components/generic.py.jinja2",
                    name=service_name,
                    **kwargs
                ))
            raise
