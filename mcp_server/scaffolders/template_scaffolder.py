# mcp_server/scaffolders/template_scaffolder.py
from __future__ import annotations

"""

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
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp_server.core.exceptions import ValidationError
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.scaffolders.base_scaffolder import BaseScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.template_introspector import introspect_template_with_inheritance
from mcp_server.scaffolding.version_hash import extract_template_version
from mcp_server.schemas import ArtifactRegistryConfig

# Project modules
if TYPE_CHECKING:
    from mcp_server.config.settings import Settings


class TemplateScaffolder(BaseScaffolder):
    """Unified scaffolder using artifact registry templates."""

    def __init__(
        self,
        registry: ArtifactRegistryConfig,
        renderer: JinjaRenderer | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize with dependency injection."""
        super().__init__()
        self.registry = registry

        # Initialize renderer with configurable template root (fail-fast)
        if renderer is None:
            from mcp_server.config.settings import Settings  # noqa: PLC0415

            effective_settings = settings or Settings.from_env()
            template_dir = effective_settings.server.resolved_template_root
            renderer = JinjaRenderer(template_dir=template_dir)
        self._renderer = renderer

    @property
    def renderer(self) -> JinjaRenderer:
        """Get the template renderer."""
        return self._renderer

    def validate(
        self,
        artifact_type: str,
        note_context: NoteContext | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> bool:
        """Validate scaffolding arguments using template introspection.

        Args:
            artifact_type: Artifact type_id from registry
            note_context: Optional NoteContext for producing SuggestionNotes
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
        template_path = self._resolve_template_path(artifact_type, artifact, kwargs)

        if not template_path:
            raise ValidationError(f"No template configured for artifact type: {artifact_type}")

        if self._renderer.env.loader is None:
            raise ValidationError(f"Template loader not configured for {artifact_type}")

        # Type guard: loader is FileSystemLoader with searchpath
        loader = self._renderer.env.loader
        if not hasattr(loader, "searchpath"):
            raise ValidationError(
                f"Template loader does not support searchpath for {artifact_type}"
            )

        template_root = Path(loader.searchpath[0])

        # Validate template version against expected version from registry (delayed validation)
        # Only validate when template_path matches the official registry template_path
        if isinstance(artifact.template_version, str) and template_path == artifact.template_path:
            actual_version = extract_template_version(template_root / template_path)

            if actual_version != artifact.template_version:
                raise ValidationError(
                    f"Template version mismatch for {artifact_type}: "
                    f"expected {artifact.template_version}, found {actual_version}"
                )
        # Extract schema from template via inheritance-aware introspection (Task 2.1)
        # This resolves the entire inheritance chain to detect ALL variables
        schema = introspect_template_with_inheritance(template_root, template_path)

        # Check required fields present
        provided = set(kwargs.keys())
        missing = [f for f in schema.required if f not in provided]

        if missing:
            error = ValidationError(
                f"Missing required fields for {artifact_type}: {', '.join(missing)}",
                schema=schema,
            )
            # Track missing/provided for structured response
            error.missing = missing
            error.provided = list(provided)
            if note_context is not None:
                note_context.produce(
                    Note(
                        key="scaffold_missing_fields_suggestion",
                        params={
                            "missing_fields": ", ".join(missing),
                            "artifact_type": artifact_type,
                        },
                    )
                )
            raise error

        return True

    def scaffold(
        self,
        artifact_type: str,
        skip_validation: bool = False,
        note_context: NoteContext | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> ScaffoldResult:
        """Scaffold artifact from template.

        Args:
            artifact_type: Artifact type_id from registry
            skip_validation: If True, skip introspection-based validation.
                 Used when Pydantic schemas have already validated input.
            note_context: Optional NoteContext for producing typed notes on error paths.
            **kwargs: Context for template rendering

        Returns:
            ScaffoldResult with rendered content

        Raises:
            ValidationError: If validation fails or template missing
        """
        # Validate via introspection when skip_validation is False.
        # When validation is done using Pydantic schemas, we skip introspection.
        if not skip_validation:
            self.validate(artifact_type, note_context=note_context, **kwargs)

        # Get artifact definition
        artifact = self.registry.get_artifact(artifact_type)

        # Get template path (handle special cases)
        template_path = self._resolve_template_path(artifact_type, artifact, kwargs)

        if not template_path:
            raise ValidationError(f"No template configured for artifact type: {artifact_type}")
        # Always validate template version against expected version (delayed validation)
        # Even if skip_validation is True (since Pydantic does not validate templates)
        loader = self._renderer.env.loader
        if loader is not None and hasattr(loader, "searchpath"):
            template_root = Path(loader.searchpath[0])
            is_valid_version = isinstance(artifact.template_version, str)
            if is_valid_version and template_path == artifact.template_path:
                actual_version = extract_template_version(template_root / template_path)

                if actual_version != artifact.template_version:
                    raise ValidationError(
                        f"Template version mismatch for {artifact_type}: "
                        f"expected {artifact.template_version}, found {actual_version}"
                    )

        # Render template via JinjaRenderer (safe FileSystemLoader)
        # Add artifact_type to render context (needed by Tier 0 SCAFFOLD block)
        # Add format (determines comment style in SCAFFOLD header)
        # Add timestamp (ISO 8601 format for provenance)
        # Add output_path (file path for SCAFFOLD header)
        # Remove template_name from context to avoid conflict
        format_value = self._determine_format(artifact)

        # Construct output path for SCAFFOLD header.
        # None = compact single-line header; absent key = fall back to name-based path.
        name = kwargs.get("name") or kwargs.get("title", "unnamed")
        suffix = artifact.name_suffix or ""
        extension = artifact.file_extension
        output_path = kwargs.get("output_path", f"{name}{suffix}{extension}")

        # Use provided timestamp or generate ISO 8601 (UTC, minute precision)
        timestamp = kwargs.get("timestamp") or datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")

        # template_version must be provided by caller (artifact_manager injects version_hash)
        template_version = kwargs.get("template_version", "1.0")

        render_context = {
            **{k: v for k, v in kwargs.items() if k not in ("template_name", "output_path")},
            "artifact_type": artifact_type,
            "format": format_value,
            "timestamp": timestamp,
            "template_version": template_version,
            "output_path": output_path,
        }
        rendered = self._load_and_render_template(template_path, **render_context)

        # Construct filename (docs use 'title', code uses 'name')
        file_name = f"{name}{suffix}{extension}"

        return ScaffoldResult(content=rendered, file_name=file_name)

    def _resolve_template_path(
        self,
        artifact_type: str,
        artifact: Any,  # noqa: ANN401
        context: dict[str, Any],
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

        # GENERAL OVERRIDE: Any artifact can override via template_name
        template_name_override = context.get("template_name")
        if template_name_override and isinstance(template_name_override, str):
            return str(template_name_override)

        # DEFAULT: Use template_path from artifacts.yaml
        template_path: str | None = artifact.template_path

        # VALIDATION: Generic without template_path requires template_name
        if artifact_type == "generic" and template_path is None:
            raise ValidationError(
                "Generic artifacts require 'template_name' in context or "
                "template_path in artifacts.yaml"
            )

        return template_path

    def _load_and_render_template(self, template_name: str, **kwargs: Any) -> str:  # noqa: ANN401
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

    def _determine_format(self, artifact: Any) -> str:  # noqa: ANN401
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
