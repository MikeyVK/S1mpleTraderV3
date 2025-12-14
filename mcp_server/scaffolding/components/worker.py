"""Worker Scaffolder Component."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError
from mcp_server.scaffolding.base import ComponentScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.utils import validate_pascal_case


class WorkerScaffolder(ComponentScaffolder):
    """Scaffolds Worker classes."""

    def __init__(self, renderer: JinjaRenderer) -> None:
        """Initialize worker scaffolder."""
        self.renderer = renderer

    def validate(self, **kwargs: Any) -> bool:
        """Validate worker arguments."""
        if "name" in kwargs:
            validate_pascal_case(kwargs["name"])
        return True

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Worker.

        Args:
            name: Worker name
            **kwargs: Worker args (input_dto, output_dto, etc.)

        Returns:
            Rendered Python code
        """
        self.validate(name=name)

        worker_name = name if name.endswith("Worker") else f"{name}Worker"

        try:
            return self.renderer.render(
                "components/worker.py.jinja2",
                name=worker_name,
                **kwargs
            )
        except ExecutionError:
            return self._render_fallback(worker_name, **kwargs)

    def _render_fallback(self, name: str, **kwargs: Any) -> str:
        """Fallback rendering."""
        input_dto = kwargs.get("input_dto", "Any")
        output_dto = kwargs.get("output_dto", "Any")
        dependencies = kwargs.get("dependencies", [])

        deps_assignments = self._render_dep_assignments(dependencies)
        deps_str = ""
        if dependencies:
            deps_str = ", " + ", ".join(dependencies)

        return f'''"""Generated Worker module."""
from typing import Any

from backend.core.interfaces.base_worker import BaseWorker


class {name}(BaseWorker[{input_dto}, {output_dto}]):
    """Worker that processes {input_dto} and produces {output_dto}."""

    def __init__(self{deps_str}) -> None:
        """Initialize the worker."""
        super().__init__()
{deps_assignments}
    async def process(self, input_data: {input_dto}) -> {output_dto}:
        """Process input and return output.

        Args:
            input_data: Input DTO to process

        Returns:
            Processed output DTO
        """
        raise NotImplementedError("Implement process method")
'''

    def _render_dep_assignments(self, dependencies: list[str] | None) -> str:
        """Render dependency assignments."""
        if not dependencies:
            return ""

        lines = []
        for dep in dependencies:
            name = dep.split(":")[0].strip()
            lines.append(f"        self.{name} = {name}")
        return "\n".join(lines) + "\n"
