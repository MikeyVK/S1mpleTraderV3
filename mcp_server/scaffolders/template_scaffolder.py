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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

# Project modules
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolders.base_scaffolder import BaseScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.template_introspector import introspect_template

if TYPE_CHECKING:
    pass  # TYPE_CHECKING block for future type-only imports


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
                     Defaults to JinjaRenderer with tier-root (mcp_server/scaffolding/templates).
        """
        super().__init__()
        self.registry = registry or ArtifactRegistryConfig.from_file()

        # Initialize renderer with configurable template root (fail-fast)
        if renderer is None:
            template_dir = get_template_root()
            renderer = JinjaRenderer(template_dir=template_dir)
        self._renderer = renderer

    def validate(self, artifact_type: str, **kwargs: Any) -> bool:
        """Validate scaffolding arguments using template introspection.

        Args:
            artifact_type: Artifact type_id from registry
            **kwargs: Context for template rendering

        Returns:
            True if validation passes

        Raises:
            ValidationError: If artifact_type unknown or required
                           fields missing (with schema attached)
        """
        # Get artifact definition (raises ConfigError if unknown)
        artifact = self.registry.get_artifact(artifact_type)

        # Get template path
        template_path = self._resolve_template_path(
            artifact_type,
            artifact,
            kwargs
        )

        if not template_path:
            raise ValidationError(
                f"No template configured for artifact type: {artifact_type}"
            )

        # Load template source for introspection
        if self._renderer.env.loader is None:
            raise ValidationError(
                f"Template loader not configured for {artifact_type}"
            )

        template_source = self._renderer.env.loader.get_source(
            self._renderer.env,
            template_path
        )[0]

        # Extract schema from template via introspection
        schema = introspect_template(self._renderer.env, template_source)

        # Check required fields present
        provided = set(kwargs.keys())
        missing = [f for f in schema.required if f not in provided]

        if missing:
            error = ValidationError(
                f"Missing required fields for {artifact_type}: "
                f"{', '.join(missing)}",
                hints=[
                    f"Required: {', '.join(schema.required)}",
                    f"Optional: {', '.join(schema.optional)}",
                    f"Missing: {', '.join(missing)}"
                ],
                schema=schema
            )
            # Track missing/provided for structured response
            error.missing = missing
            error.provided = list(provided)
            raise error

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
        # Add artifact_type to render context (needed by Tier 0 SCAFFOLD block)
        # Add format (determines comment style in SCAFFOLD header)
        # Add timestamp (ISO 8601 format for provenance)
        # Add output_path (file path for SCAFFOLD header)
        # Remove template_name from context to avoid conflict
        format_value = self._determine_format(artifact)

        # Construct output path for SCAFFOLD header
        name = kwargs.get("name") or kwargs.get("title", "unnamed")
        suffix = artifact.name_suffix or ""
        extension = artifact.file_extension
        output_path = kwargs.get("output_path") or f"{name}{suffix}{extension}"

        # Generate ISO 8601 timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        render_context = {
            **{k: v for k, v in kwargs.items() if k not in ("template_name", "output_path")},
            "artifact_type": artifact_type,
            "format": format_value,
            "timestamp": timestamp,
            "output_path": output_path
        }
        rendered = self._load_and_render_template(template_path, **render_context)

        # Construct filename (docs use 'title', code uses 'name')
        file_name = f"{name}{suffix}{extension}"

        return ScaffoldResult(content=rendered, file_name=file_name)

    def _resolve_template_path(
        self,
        artifact_type: str,
        artifact: Any,
        context: dict[str, Any]
    ) -> str | None:
        """Resolve template path from artifact definition or context.

        Resolution order:
        1. Service artifacts: Check service_type in context (command/orchestrator/query)
        2. Generic artifacts: Check template_name in context (PRIORITY override)
        3. Default: Use artifact.template_path from artifacts.yaml
        4. Validation: Generic with no template_path AND no template_name = error

        Args:
            artifact_type: Artifact type_id
            artifact: Artifact definition from registry
            context: Template rendering context

        Returns:
            Relative template path or None
        """
        # SPECIAL CASE 1: Service can select subtype via service_type context
        if artifact_type == "service":
            service_type = context.get("service_type", "command")  # Default: command
            service_template_map: dict[str, str] = {
                "orchestrator": "concrete/service_orchestrator.py.jinja2",
                "command": "concrete/service_command.py.jinja2",
                "query": "concrete/service_query.py.jinja2",
            }
            # Get template from map or fall back to artifact.template_path
            template = service_template_map.get(service_type)
            return template if template else artifact.template_path

        # SPECIAL CASE 2: Generic can override via template_name in context
        if artifact_type == "generic":
            template_name = context.get("template_name")
            if template_name and isinstance(template_name, str):
                return str(template_name)  # PRIORITY: context overrides artifacts.yaml

        # DEFAULT: Use template_path from artifacts.yaml
        template_path: str | None = artifact.template_path

        # VALIDATION: Generic without template_path requires template_name
        if artifact_type == "generic" and template_path is None:
            raise ValidationError(
                "Generic artifacts require 'template_name' in context or "
                "template_path in artifacts.yaml"
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

    def _determine_format(self, artifact: Any) -> str:
        """Determine format for SCAFFOLD header comment style.

        Args:
            artifact: Artifact definition

        Returns:
            Format string: "python", "yaml", "markdown", "shell", etc.
        """
        extension = artifact.file_extension.lstrip(".")

        # Map file extensions to format names
        format_map = {
            "py": "python",
            "yaml": "yaml",
            "yml": "yaml",
            "md": "markdown",
            "sh": "shell",
            "bash": "shell",
        }

        return format_map.get(extension, "markdown")  # Default to markdown (<!-- -->)
