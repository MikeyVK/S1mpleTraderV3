"""Jinja2 template renderer."""
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from mcp_server.core.exceptions import ExecutionError


class JinjaRenderer:
    """Handles Jinja2 template rendering."""

    def __init__(self, template_dir: Path | None = None) -> None:
        """Initialize the renderer.

        Args:
            template_dir: Path to templates directory.
        """
        if template_dir:
            self.template_dir = template_dir
        else:
            # Default to mcp_server/templates relative to this package
            parent = Path(__file__).parent.parent
            self.template_dir = parent / "templates"

        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get or create the Jinja2 environment."""
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )
        return self._env

    def get_template(self, template_name: str) -> Any:  # noqa: ANN401
        """Load a template by name.

        Args:
            template_name: Relative path to template

        Returns:
            Loaded Jinja2 template

        Raises:
            ExecutionError: If template not found
        """
        try:
            return self.env.get_template(template_name)
        except TemplateNotFound as e:
            raise ExecutionError(
                f"Template not found: {template_name}",
                recovery=["Check template directory structure"]
            ) from e

    def render(self, template_name: str, **kwargs: Any) -> str:  # noqa: ANN401
        """Render a template with variables.

        Args:
            template_name: Relative path to template
            **kwargs: Template variables

        Returns:
            Rendered string
        """
        template = self.get_template(template_name)
        return str(template.render(**kwargs))

    def list_templates(self) -> list[str]:
        """List all available templates.

        Returns:
            List of template names
        """
        templates: list[str] = []
        if self.template_dir.exists():
            for path in self.template_dir.rglob("*.jinja2"):
                templates.append(str(path.relative_to(self.template_dir)))
        return templates
