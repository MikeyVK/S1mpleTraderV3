# backend/services/template_engine.py
"""Template Engine - Jinja2 rendering for scaffolding.

Provides Jinja2-based template rendering for Issue #72 5-tier architecture.
Extracted from mcp_server/scaffolding/renderer.py for reusability (Issue #108).

@layer: Backend (Services)
@dependencies: [jinja2, pathlib, re]
@responsibilities:
    - Render Jinja2 templates with context variables
    - Support 5-tier template inheritance (FileSystemLoader)
    - Provide custom filters (pascalcase, snakecase, kebabcase, validate_identifier)
    - Raise clear errors for missing templates or invalid configuration
"""

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template


class TemplateEngine:
    """Jinja2 template rendering engine.

    Handles template rendering for scaffolding with support for Issue #72
    5-tier template architecture ({% extends %} inheritance).
    """

    def __init__(self, template_root: Path | str) -> None:
        """Initialize the template engine.

        Args:
            template_root: Path to templates root directory (Path or str)

        Raises:
            ValueError: If template_root does not exist
        """
        self.template_root = Path(template_root)

        if not self.template_root.exists():
            raise ValueError(f"Template root does not exist: {self.template_root}")

        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Get or create the Jinja2 environment.

        Lazy initialization to avoid overhead if not used.
        Registers custom filters on first access.

        Returns:
            Configured Jinja2 Environment
        """
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(self.template_root)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )

            # Register custom filters
            self._env.filters["pascalcase"] = self._filter_pascalcase
            self._env.filters["snakecase"] = self._filter_snakecase
            self._env.filters["kebabcase"] = self._filter_kebabcase
            self._env.filters["validate_identifier"] = self._filter_validate_identifier

        return self._env

    def get_template(self, template_name: str) -> Template:
        """Load a template by name.

        Args:
            template_name: Relative path to template (e.g., "concrete/dto.py.jinja2")

        Returns:
            Loaded Jinja2 Template object

        Raises:
            TemplateNotFound: If template does not exist
        """
        return self.env.get_template(template_name)

    def render(self, template_name: str, **kwargs: Any) -> str:  # noqa: ANN401
        """Render a template with variables.

        Args:
            template_name: Relative path to template
            **kwargs: Template context variables

        Returns:
            Rendered string output

        Raises:
            TemplateNotFound: If template does not exist
            Exception: If template rendering fails (missing variables, etc.)

        Example:
            >>> engine = TemplateEngine(template_root="mcp_server/scaffolding/templates")
            >>> output = engine.render("concrete/dto.py.jinja2", name="UserDTO", ...)
        """
        template = self.get_template(template_name)
        return str(template.render(**kwargs))

    def list_templates(self) -> list[str]:
        """List all available templates.

        Returns:
            List of template names (relative paths to .jinja2 files)

        Example:
            >>> engine = TemplateEngine(template_root="mcp_server/scaffolding/templates")
            >>> templates = engine.list_templates()
            >>> print(templates)
            ['concrete/dto.py.jinja2', 'tier0_base_artifact.jinja2', ...]
        """
        templates: list[str] = []
        if self.template_root.exists():
            for path in self.template_root.rglob("*.jinja2"):
                # Use forward slashes for cross-platform compatibility
                rel_path = path.relative_to(self.template_root).as_posix()
                templates.append(rel_path)
        return templates

    # Custom Jinja2 filters

    @staticmethod
    def _filter_pascalcase(value: str) -> str:
        """Convert string to PascalCase.

        Args:
            value: Input string (snake_case, kebab-case, or mixed)

        Returns:
            PascalCase string

        Example:
            >>> _filter_pascalcase("test_name")
            'TestName'
        """
        # Split on underscores, hyphens, and existing capitals
        words = re.split(r"[_\-]+", value)
        return "".join(word.capitalize() for word in words if word)

    @staticmethod
    def _filter_snakecase(value: str) -> str:
        """Convert string to snake_case.

        Args:
            value: Input string (PascalCase, kebab-case, or mixed)

        Returns:
            snake_case string

        Example:
            >>> _filter_snakecase("TestName")
            'test_name'
        """
        # Insert underscore before capitals (except first)
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
        # Insert underscore before capital sequences
        s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
        # Replace hyphens with underscores
        s3 = s2.replace("-", "_")
        return s3.lower()

    @staticmethod
    def _filter_kebabcase(value: str) -> str:
        """Convert string to kebab-case.

        Args:
            value: Input string (PascalCase, snake_case, or mixed)

        Returns:
            kebab-case string

        Example:
            >>> _filter_kebabcase("TestName")
            'test-name'
        """
        # Use snakecase logic, then replace underscores with hyphens
        snake = TemplateEngine._filter_snakecase(value)
        return snake.replace("_", "-")

    @staticmethod
    def _filter_validate_identifier(value: str) -> str:
        """Validate and return Python identifier.

        Args:
            value: String to validate as Python identifier

        Returns:
            Original value if valid identifier

        Raises:
            ValueError: If value is not a valid Python identifier

        Example:
            >>> _filter_validate_identifier("valid_name")
            'valid_name'
            >>> _filter_validate_identifier("123invalid")
            ValueError: Invalid Python identifier: 123invalid
        """
        if not value.isidentifier():
            raise ValueError(f"Invalid Python identifier: {value}")
        return value
