"""Worker Scaffolder Component."""
from typing import Any

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

        return str(self.renderer.render(
            "components/worker.py.jinja2",
            name=worker_name,
            **kwargs
        ))
