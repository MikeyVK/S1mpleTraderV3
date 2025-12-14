"""Worker Scaffolder Component."""
from typing import Any
from mcp_server.core.exceptions import ExecutionError

from mcp_server.scaffolding.base import BaseScaffolder


class WorkerScaffolder(BaseScaffolder):
    """Scaffolds Worker components."""

    def scaffold(self, name: str, **kwargs: Any) -> str:
        """Scaffold a Worker.

        Args:
            name: Worker name
            **kwargs: Worker arguments

        Returns:
            Rendered Python code
        """
        self.validate(name=name)
        worker_name = name if name.endswith("Worker") else f"{name}Worker"

        try:
            return str(self.renderer.render(
                "components/worker.py.jinja2",
                name=worker_name,
                **kwargs
            ))
        except ExecutionError:
            input_type = kwargs.get("input_type", "In")
            output_type = kwargs.get("output_type", "Out")
            deps: list[str] | None = kwargs.get("dependencies")
            lines = [f"class {worker_name}(BaseWorker[{input_type}, {output_type}]):"]
            if deps:
                lines.append("    def __init__(self) -> None:")
                for dep in deps:
                    attr = dep.split(":")[0].strip()
                    lines.append(f"        self.{attr} = {attr}")
            else:
                lines.append("    def __init__(self) -> None:")
                lines.append("        pass")
            return "\n".join(lines)
