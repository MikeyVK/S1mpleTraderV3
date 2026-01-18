# mcp_server/scaffolders/template_scaffolder.py
"""
TemplateScaffolder - Unified template-based artifact scaffolding.

Single scaffolder implementation that replaces 9 separate scaffolder classes.
Uses Jinja2 for template rendering and artifact registry for configuration.

@layer: Backend (Scaffolders)
@dependencies: [jinja2, ArtifactRegistryConfig, BaseScaffolder]
@responsibilities:
    - Load templates from artifact registry
    - Render templates with Jinja2
    - Validate required fields
    - Return scaffolded content as ScaffoldResult
"""

from typing import Any

from jinja2 import Template, TemplateError

from mcp_server.scaffolders.base_scaffolder import BaseScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.errors import ConfigError, ValidationError


class TemplateScaffolder(BaseScaffolder):
    """Unified scaffolder using artifact registry templates."""

    def __init__(
        self, registry: ArtifactRegistryConfig | None = None
    ) -> None:
        """Initialize with optional dependency injection."""
        super().__init__()
        self.registry = registry or ArtifactRegistryConfig.from_file()

    def validate(self, artifact_type: str, **kwargs: Any) -> bool:
        """Validate scaffolding arguments.
        
        Args:
            artifact_type: Artifact type_id from registry
            **kwargs: Context for template rendering
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If artifact_type unknown or required fields missing
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
            ValidationError: If validation fails
            ConfigError: If template not found
        """
        # Validate first
        self.validate(artifact_type, **kwargs)

        # Get artifact definition
        artifact = self.registry.get_artifact(artifact_type)

        # Check template exists
        if not artifact.template_path and not artifact.fallback_template:
            raise ConfigError(
                f"No template defined for artifact type: {artifact_type}"
            )

        # Load and render template (Cycle 5)
        template_path = artifact.template_path or artifact.fallback_template
        rendered = self._load_and_render_template(template_path, **kwargs)

        # Construct filename
        name = kwargs.get("name", "unnamed")
        suffix = artifact.name_suffix or ""
        extension = artifact.file_extension
        file_name = f"{name}{suffix}{extension}"

        return ScaffoldResult(content=rendered, file_name=file_name)

    def _load_and_render_template(
        self, template_path: str, **kwargs: Any
    ) -> str:
        """Load template from filesystem and render (Cycle 5).
        
        Args:
            template_path: Path to template file
            **kwargs: Template context
        
        Returns:
            Rendered template content
        
        Raises:
            ConfigError: If template cannot be loaded
        """
        try:
            # Read template file
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Render template with Jinja2 (Cycle 6 complete)
            try:
                template = Template(template_content)
                rendered = template.render(**kwargs)
                return rendered
            except TemplateError as e:
                raise ConfigError(
                    f"Template rendering failed: {template_path}\n{str(e)}",
                    file_path=template_path
                ) from e

        except FileNotFoundError as e:
            raise ConfigError(
                f"Template file not found: {template_path}",
                file_path=template_path
            ) from e
        except (IOError, PermissionError) as e:
            raise ConfigError(
                f"Failed to read template: {template_path}\n{str(e)}",
                file_path=template_path
            ) from e
