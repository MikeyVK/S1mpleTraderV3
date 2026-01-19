# mcp_server/scaffolders/template_scaffolder.py
"""
TemplateScaffolder - Unified template-based artifact scaffolding.

Single scaffolder implementation that replaces 9 separate scaffolder classes.
Uses JinjaRenderer with FileSystemLoader for safe template loading.

@layer: Backend (Scaffolders)
@dependencies: [
    jinja2,
    ArtifactRegistryConfig,
    BaseScaffolder,
    JinjaRenderer
]
@responsibilities:
    - Load templates via JinjaRenderer (safe FileSystemLoader)
    - Render templates with relative paths
    - Validate required fields from registry
    - Return scaffolded content as ScaffoldResult
"""

# Standard library
from pathlib import Path
from typing import Any

# Project modules
from mcp_server.core.exceptions import ValidationError
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.scaffolders.base_scaffolder import BaseScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.scaffolding.renderer import JinjaRenderer


class TemplateScaffolder(BaseScaffolder):
    """Unified scaffolder using artifact registry templates."""

    def __init__(
        self,
        registry: ArtifactRegistryConfig | None = None,
        renderer: JinjaRenderer | None = None
    ) -> None:
        """Initialize with dependency injection.

        Args:
            registry: Artifact registry configuration.
                     Defaults to loading from .st3/artifacts.yaml.
            renderer: Jinja2 template renderer.
                     Defaults to JinjaRenderer with mcp_server/templates.
        """
        super().__init__()
        self.registry = registry or ArtifactRegistryConfig.from_file()

        # Initialize renderer with safe FileSystemLoader
        if renderer is None:
            # Default template directory: mcp_server/templates
            template_dir = Path(__file__).parent.parent / "templates"
            renderer = JinjaRenderer(template_dir=template_dir)
        self._renderer = renderer

    def validate(self, artifact_type: str, **kwargs: Any) -> bool:
        """Validate scaffolding arguments.

        Args:
            artifact_type: Artifact type_id from registry
            **kwargs: Context for template rendering

        Returns:
            True if validation passes

        Raises:
            ValidationError: If artifact_type unknown or required
                           fields missing
        """
        # Get artifact definition (raises ConfigError if unknown)
        artifact = self.registry.get_artifact(artifact_type)

        # Check required fields present
        missing = [f for f in artifact.required_fields if f not in kwargs]
        if missing:
            raise ValidationError(
                f"Missing required fields for {artifact_type}: "
                f"{', '.join(missing)}"
            )

        return True

    def scaffold(self, artifact_type: str, **kwargs: Any) -> ScaffoldResult:
        """Scaffold artifact from template.

        Args:
            artifact_type: Artifact type_id from registry
            **kwargs: Context for template rendering

        Returns:
            ScaffoldResult with rendered content

        Raises:
            ValidationError: If validation fails or template missing
        """
        # Validate first
        self.validate(artifact_type, **kwargs)

        # Get artifact definition
        artifact = self.registry.get_artifact(artifact_type)

        # Get template path (handle special cases)
        template_path = self._resolve_template_path(
            artifact_type,
            artifact,
            kwargs
        )

        if not template_path:
            raise ValidationError(
                f"No template configured for artifact type: {artifact_type}"
            )

        # Render template via JinjaRenderer (safe FileSystemLoader)
        # Remove template_name from context to avoid conflict
        render_context = {k: v for k, v in kwargs.items() if k != "template_name"}
        rendered = self._load_and_render_template(template_path, **render_context)

        # Construct filename (docs use 'title', code uses 'name')
        name = kwargs.get("name") or kwargs.get("title", "unnamed")
        suffix = artifact.name_suffix or ""
        extension = artifact.file_extension
        file_name = f"{name}{suffix}{extension}"

        return ScaffoldResult(content=rendered, file_name=file_name)

    def _resolve_template_path(
        self,
        artifact_type: str,
        artifact: Any,
        context: dict[str, Any]
    ) -> str | None:
        """Resolve template path for artifact type.

        Handles special cases:
        - service: Uses service_type to select template
        - generic: Uses template_name from context

        Args:
            artifact_type: Artifact type_id
            artifact: Artifact definition from registry
            context: Template rendering context

        Returns:
            Relative template path or None
        """
        template_path: str | None = artifact.template_path

        # SPECIAL CASE: Service type selects template
        if artifact_type == "service" and template_path is None:
            service_type = context.get("service_type", "orchestrator")
            template_path = f"components/service_{service_type}.py.jinja2"

        # SPECIAL CASE: Generic uses template_name from context
        elif artifact_type == "generic" and template_path is None:
            template_path = context.get("template_name")
            if not template_path:
                raise ValidationError(
                    "Generic artifacts require 'template_name' in context"
                )

        return template_path

    def _load_and_render_template(
        self,
        template_name: str,
        **kwargs: Any
    ) -> str:
        """Load and render template using JinjaRenderer.

        Uses FileSystemLoader for safe template access (no arbitrary
        file reading). Template name is relative to templates/ root.

        Args:
            template_name: Template path relative to templates/
                          e.g. "components/dto.py.jinja2"
            **kwargs: Template context variables

        Returns:
            Rendered template content

        Raises:
            ExecutionError: If template not found or rendering fails
                          (raised by JinjaRenderer with recovery hints)
        """
        # Let ExecutionError propagate - semantically correct
        # (template loading is execution/config, not input validation)
        return self._renderer.render(template_name, **kwargs)
