"""Unified template-based scaffolder (Cycle 4).

Single scaffolder that replaces 9 separate scaffolder classes.
Issue #56: Unified artifact system.
"""

from typing import Any

from mcp_server.scaffolders.base_scaffolder import BaseScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.config.artifact_registry_config import (
    ArtifactRegistryConfig,
    ConfigError,
)
from mcp_server.core.errors import ValidationError


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

        # Render template (placeholder for Cycle 5)
        rendered = self._render_template(artifact, **kwargs)

        # Construct filename
        name = kwargs.get("name", "unnamed")
        suffix = artifact.name_suffix or ""
        extension = artifact.file_extension
        file_name = f"{name}{suffix}{extension}"

        return ScaffoldResult(content=rendered, file_name=file_name)

    def _render_template(
        self, artifact: Any, **kwargs: Any
    ) -> str:
        """Placeholder for template rendering (Cycle 5)."""
        return f"# Placeholder for {kwargs.get('name', 'artifact')}"
