# mcp_server/managers/artifact_manager.py
"""
ArtifactManager - Orchestrates artifact scaffolding operations.

Manages the complete artifact scaffolding workflow including template rendering,
validation, directory resolution, and file writing. Implements dependency injection
pattern for testability.

@layer: Backend (Managers)
@dependencies: [ArtifactRegistryConfig, TemplateScaffolder, ValidationService,
               DirectoryPolicyResolver, FilesystemAdapter]
@responsibilities:
    - Orchestrate artifact scaffolding workflow
    - Resolve output paths via DirectoryPolicyResolver
    - Handle generic artifact special cases
    - Validate scaffolded content before writing
    - Write scaffolded content to filesystem
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.template_registry import TemplateRegistry
from mcp_server.scaffolding.version_hash import compute_version_hash
from mcp_server.schemas import (
    ArtifactDefinition,
    ArtifactRegistryConfig,
    ProjectStructureConfig,
)
from mcp_server.schemas.base import BaseContext, BaseRenderContext
from mcp_server.validation.template_analyzer import TemplateAnalyzer
from mcp_server.validation.validation_service import ValidationService

logger = logging.getLogger(__name__)

# Schema pipeline contexts are loaded dynamically from ArtifactDefinition in artifacts.yaml


@dataclass
class ArtifactManagerDependencies:
    """Dependency injection container for ArtifactManager."""

    registry: ArtifactRegistryConfig
    scaffolder: TemplateScaffolder | None = None
    validation_service: ValidationService | None = None
    fs_adapter: FilesystemAdapter | None = None
    template_registry: Any | None = None
    project_structure_config: ProjectStructureConfig | None = None


class ArtifactManager:
    """Manages artifact scaffolding operations.

    NOT a singleton - each tool instantiates its own manager.
    Provides dependency injection for all collaborators.
    """

    def _require_registry(self) -> ArtifactRegistryConfig:
        """Return the configured artifact registry."""
        return self.registry

    def __init__(
        self,
        dependencies: ArtifactManagerDependencies | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialize manager with optional dependencies.

        Supports both new-style (dependencies container) and legacy-style
        (individual keyword arguments) for backwards compatibility.

        Note:
            The test harness and some callers may pass a legacy/compat keyword
            argument `workspace_root`. When provided and fs_adapter is not passed,
            this is used to scope the default FilesystemAdapter.

        Args:
            dependencies: Dependency injection container (preferred)
            **kwargs: Legacy support for individual dependencies and workspace_root
        """
        workspace_root = kwargs.pop("workspace_root", None)
        server_root = kwargs.pop("server_root", None)

        # Legacy compat: accept individual keyword arguments
        registry = kwargs.pop("registry", None)
        scaffolder = kwargs.pop("scaffolder", None)
        validation_service = kwargs.pop("validation_service", None)
        fs_adapter = kwargs.pop("fs_adapter", None)
        template_registry = kwargs.pop("template_registry", None)
        project_structure_config = kwargs.pop("project_structure_config", None)

        if kwargs:
            unexpected = ", ".join(sorted(kwargs.keys()))
            raise TypeError(f"Unexpected keyword arguments: {unexpected}")

        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        if server_root is None:
            raise ValueError(
                "ArtifactManager requires server_root. "
                "Pass server_root=workspace_root / settings.server.server_root_dir from server.py."
            )
        self.server_root = Path(server_root).resolve()

        # Merge dependencies container with individual kwargs (kwargs take precedence)
        deps = dependencies
        registry = (
            registry if registry is not None else (deps.registry if deps is not None else None)
        )
        scaffolder = (
            scaffolder
            if scaffolder is not None
            else (deps.scaffolder if deps is not None else None)
        )
        validation_service = (
            validation_service
            if validation_service is not None
            else (deps.validation_service if deps is not None else None)
        )
        fs_adapter = (
            fs_adapter
            if fs_adapter is not None
            else (deps.fs_adapter if deps is not None else None)
        )
        template_registry = (
            template_registry
            if template_registry is not None
            else (deps.template_registry if deps is not None else None)
        )
        project_structure_config = (
            project_structure_config
            if project_structure_config is not None
            else (deps.project_structure_config if deps is not None else None)
        )

        fs_root = getattr(fs_adapter, "root_path", None)
        candidate_roots: list[Path] = []
        if self.workspace_root is not None:
            candidate_roots.append(self.workspace_root)
        if isinstance(fs_root, str | os.PathLike):
            candidate_roots.append(Path(fs_root).resolve())
        candidate_roots.append(Path.cwd().resolve())

        if registry is None and scaffolder is not None:
            registry = getattr(scaffolder, "registry", None)

        if registry is None:
            raise ValueError("ArtifactRegistryConfig must be injected into ArtifactManager")

        self.registry: ArtifactRegistryConfig = cast(ArtifactRegistryConfig, registry)
        self._project_structure_config: ProjectStructureConfig | None = project_structure_config
        self._directory_resolver: DirectoryPolicyResolver | None = (
            DirectoryPolicyResolver(project_structure_config)
            if project_structure_config is not None
            else None
        )
        self.scaffolder = scaffolder or TemplateScaffolder(registry=self.registry)
        self.validation_service = validation_service or ValidationService()

        if fs_adapter is None and self.workspace_root is not None:
            fs_adapter = FilesystemAdapter(root_path=str(self.workspace_root))
        self.fs_adapter = fs_adapter or FilesystemAdapter()

        # Task 1.1c: Template registry for provenance (lazy init if not provided)
        # IMPORTANT: resolve path relative to server_root (never process CWD or the state root).
        if template_registry is None:
            registry_path = self.server_root / "template_registry.json"
            template_registry = TemplateRegistry(registry_path=registry_path)
        self.template_registry = template_registry

    def _get_template_root(self) -> Path:
        """Resolve template root from the injected scaffolder renderer."""
        renderer = getattr(self.scaffolder, "_renderer", None)
        loader = getattr(getattr(renderer, "env", None), "loader", None)
        searchpath = getattr(loader, "searchpath", None)
        if (
            isinstance(searchpath, list | tuple)
            and searchpath
            and isinstance(searchpath[0], str | os.PathLike)
        ):
            return Path(searchpath[0])
        logger.warning("Template loader missing usable search path; falling back to cwd")
        return Path.cwd()

    def _build_dynamic_model(
        self,
        artifact_type: str,
        artifact: ArtifactDefinition,
        base_class: type[BaseModel],
    ) -> type[BaseModel]:
        """Build a dynamic frozen Pydantic model for context validation."""
        from typing import Any  # noqa: PLC0415

        from pydantic import ConfigDict, Field, create_model  # noqa: PLC0415

        fields: dict[str, Any] = {}

        context_schema = getattr(artifact, "context_schema", None)
        if not isinstance(context_schema, dict):
            raise ConfigError(f"No Context schema defined for artifact type '{artifact_type}'.")

        model_config = ConfigDict(frozen=True, extra="forbid")
        for field_name, field_def in context_schema.items():
            # Map type string to python type
            if field_def.type == "string":
                field_type: Any = str
            elif field_def.type == "integer":
                field_type = int
            elif field_def.type == "boolean":
                field_type = bool
            elif field_def.type == "array":
                if field_def.items and field_def.items.get("type") == "string":
                    field_type = list[str]
                else:
                    field_type = list[Any]
            else:
                field_type = Any

            # Handle optional vs required
            if not field_def.required:
                field_type = field_type | None
                default_val = field_def.default
            else:
                default_val = field_def.default if field_def.default is not None else ...

            # Build Field(...)
            field_kwargs: dict[str, Any] = {
                "title": field_def.title,
                "description": field_def.description,
            }
            if field_def.min_length is not None:
                field_kwargs["min_length"] = field_def.min_length
            if field_def.pattern is not None:
                field_kwargs["pattern"] = field_def.pattern

            fields[field_name] = (field_type, Field(default_val, **field_kwargs))

        # Create model name based on snake_case type_id
        model_name = f"{artifact_type.title().replace('_', '')}Dynamic{base_class.__name__}"

        return create_model(model_name, __base__=base_class, __config__=model_config, **fields)

    def _enrich_schema_context(
        self, context: BaseContext, artifact_type: str, provided_output_path: str | None = None
    ) -> BaseRenderContext:
        """Enrich template context with schema validation.

        This method is kept for backward compatibility with existing tests
        and delegates to the dynamic model builder.
        """
        artifact = self.registry.get_artifact(artifact_type)
        dynamic_model = self._build_dynamic_model(artifact_type, artifact, BaseRenderContext)
        now_utc = datetime.now(UTC)

        # Resolve output_path
        output_path_value: Path | None = None
        if provided_output_path is not None:
            output_path_value = Path(provided_output_path)
        else:
            context_dict = context.model_dump()
            if "output_path" in context_dict:
                output_path_value = Path(context_dict["output_path"])
            else:
                name = context_dict.get("name", "unnamed")
                output_path_value = self.get_artifact_path(artifact_type, name)

        # Instantiate dynamic model
        return cast(
            BaseRenderContext,
            dynamic_model(
                **context.model_dump(),
                template_id=artifact_type,
                scaffold_created=now_utc,
                version_hash="00000000",
                output_path=output_path_value,
            ),
        )

    def _extract_tier_chain(self, template_file: str) -> list[tuple[str, str]]:
        """Extract tier chain with real template names and versions from TEMPLATE_METADATA.

        CRITICAL: compute_version_hash() expects [(template_name, version), ...]
        NOT [(tier, template_id), ...]. We must extract version from TEMPLATE_METADATA.

        Args:
            template_file: Relative path to template (e.g., "concrete/dto.py.jinja2")

        Returns:
            List of (template_name, version) tuples from concrete to tier0.
            Example: [("dto", "1.0"), ("tier2_base_python", "2.0"), ...]

        Note:
            Returns empty list if extraction fails (pragmatic fallback to avoid blocking).
        """
        try:
            # Get templates root
            template_root = self._get_template_root()

            # Initialize analyzer
            analyzer = TemplateAnalyzer(template_root=template_root)

            # Get full inheritance chain
            template_path = template_root / template_file
            if not template_path.exists():
                logger.warning("Template not found for tier extraction: %s", template_file)
                return []

            chain_paths = analyzer.get_inheritance_chain(template_path)

            # Extract (template_name, version) from TEMPLATE_METADATA in each template
            tier_chain: list[tuple[str, str]] = []
            for path in chain_paths:
                # Extract metadata from template file (API expects Path, not string)
                try:
                    metadata = analyzer.extract_metadata(path)

                    # Get template name (stem without .jinja2 suffix)
                    template_name = path.stem

                    # Get version from metadata (default to "1.0" if missing)
                    version = metadata.get("version", "1.0") if metadata else "1.0"

                    tier_chain.append((template_name, version))

                except (OSError, ValueError) as e:
                    # Log but continue - use fallback for this template
                    logger.warning("Failed to read metadata from %s: %s", path, e)
                    template_name = path.stem
                    tier_chain.append((template_name, "1.0"))

            return tier_chain

        except (OSError, ValueError) as e:
            # Pragmatic: log and return empty list (don't block scaffolding)
            logger.warning("Failed to extract tier chain for %s: %s", template_file, e)
            return []

    def _build_tier_versions_dict(
        self, template_file: str, tier_chain: list[tuple[str, str]]
    ) -> dict[str, tuple[str, str]]:
        """Build tier_versions dict for registry from tier_chain.

        Args:
            template_file: Relative template path for tier inference
            tier_chain: List of (template_name, version) tuples

        Returns:
            Dict mapping tier names to (template_id, version) tuples.
            Example: {"concrete": ("dto", "1.0"), "tier2": ("tier2_base_python", "2.0")}
        """
        tier_versions: dict[str, tuple[str, str]] = {}

        try:
            template_root = self._get_template_root()
            analyzer = TemplateAnalyzer(template_root=template_root)

            template_path = template_root / template_file
            if not template_path.exists():
                return {}

            chain_paths = analyzer.get_inheritance_chain(template_path)

            # Map each path to its tier and combine with version from tier_chain
            for idx, path in enumerate(chain_paths):
                if idx >= len(tier_chain):
                    break

                parts = path.relative_to(template_root).parts

                # Determine tier from path structure
                tier = (
                    parts[0]
                    if len(parts) >= 2
                    and parts[0] in ("concrete", "tier0", "tier1", "tier2", "tier3")
                    else "tier0"
                    if len(parts) == 1
                    else None
                )

                if tier is None:
                    continue

                tier_versions[tier] = tier_chain[idx]

        except (OSError, ValueError, IndexError) as e:
            logger.warning("Failed to build tier_versions dict: %s", e)

        return tier_versions

    def _prepare_scaffold_metadata(
        self, artifact_type: str, template_file: str
    ) -> tuple[str, list[tuple[str, str]]]:
        """Prepare metadata for scaffolding (version_hash, tier_chain).

        Args:
            artifact_type: Artifact type from registry
            template_file: Template file path

        Returns:
            Tuple of (version_hash, tier_chain)
        """
        # QA-4: Extract real tier chain via introspection
        tier_chain = self._extract_tier_chain(template_file)

        # Compute version hash
        version_hash = compute_version_hash(
            artifact_type=artifact_type, template_file=template_file or "", tier_chain=tier_chain
        )

        # Timestamp is generated by template_scaffolder (centralized)
        return version_hash, tier_chain

    def _persist_provenance(
        self,
        artifact_type: str,
        version_hash: str,
        template_file: str,
        tier_chain: list[tuple[str, str]],
    ) -> None:
        """Persist provenance to template registry.

        Args:
            artifact_type: Artifact type
            version_hash: Version hash
            template_file: Template file path
            tier_chain: Tier chain
        """
        if self.template_registry is None:
            return

        tier_versions = self._build_tier_versions_dict(template_file, tier_chain)

        self.template_registry.save_version(
            artifact_type=artifact_type, version_hash=version_hash, tier_versions=tier_versions
        )

    def _resolve_output_path(
        self, artifact_type: str, output_path: str | None, enriched_context: dict[str, Any]
    ) -> str:
        """Resolve output path for artifact."""
        if output_path is not None:
            return output_path

        if artifact_type == "generic":
            if "output_path" not in enriched_context:
                raise ValidationError(
                    "Generic artifacts require explicit output_path in context",
                    error_code="generic_output_path_required",
                    params={},
                )
            return str(enriched_context["output_path"])

        name = enriched_context.get("name", "unnamed")
        artifact_path = self.get_artifact_path(artifact_type, name)
        return str(artifact_path)

    async def _validate_and_write(
        self, artifact_type: str, output_path: str, content: str, explicit: bool = False
    ) -> str:
        """Validate content and write to file.

        Args:
            artifact_type: Artifact type_id from registry
            output_path: Resolved output path
            content: Rendered artifact content
            explicit: True if output_path was explicitly provided by the caller.
                      When True, always writes to output_path even for ephemeral artifacts.
        """
        artifact = self.registry.get_artifact(artifact_type)

        passed, issues = await self.validation_service.validate(output_path, content)

        if not passed:
            if artifact.strict_validation:
                raise ValidationError(
                    f"Generated {artifact_type} artifact failed validation",
                    error_code="artifact_validation_failed",
                    params={"artifact_type": artifact_type, "issues": issues},
                )
            logger.warning(
                "Validation issues in %s artifact (type=%s), writing anyway: %r",
                artifact_type,
                artifact.type,
                issues,
            )

        if artifact.output_type == "ephemeral" and not explicit:
            temp_dir = self.server_root / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            ext = artifact.file_extension
            temp_filename = f"{artifact_type}_{uuid.uuid4().hex[:8]}{ext}"
            temp_path = temp_dir / temp_filename

            temp_path.write_text(content, encoding="utf-8")
            return str(temp_path)

        self.fs_adapter.write_file(output_path, content)
        return str(self.fs_adapter.resolve_path(output_path))

    async def scaffold_artifact(
        self,
        artifact_type: str,
        output_path: str | None = None,
        note_context: NoteContext | None = None,
        **context: Any,  # noqa: ANN401
    ) -> str:
        """Scaffold artifact from template and write to file.

        Declarative schema-typed validation:
        1. Validate user input via dynamic Context schema from registry
        2. Enrich to RenderContext (adds lifecycle fields)
        3. Render with schema-typed context
        Args:
            artifact_type: Artifact type_id from registry
            output_path: Optional explicit output path (overrides auto-resolution)
            **context: Template rendering context

        Returns:
            Absolute path to created file

        Raises:
            ValidationError: If validation fails for code artifacts (BLOCK policy)
            ConfigError: If template not found
        """
        # 0. If output_path provided, add to context before enrichment
        if output_path is not None:
            context = {**context, "output_path": output_path}

        # Get artifact and validate template exists
        artifact = self.registry.get_artifact(artifact_type)
        template_file = artifact.template_path

        # C2 gate: require output_path for file artifacts (Issue #239 C2)
        if getattr(artifact, "output_type", None) == "file" and not output_path:
            raise ValidationError(
                f"Missing output_path for file artifact '{artifact_type}'",
                error_code="missing_output_path",
                params={"artifact_type": artifact_type},
            )

        # QA-2: Fail-fast if template_path is null (not yet implemented)
        if template_file is None:
            raise ConfigError(
                f"Artifact type '{artifact_type}' has no template configured (template_path=null). "
                f"This artifact type is not yet implemented."
            )

        # Task 1.1c: Prepare metadata (version_hash, tier_chain)
        version_hash, tier_chain = self._prepare_scaffold_metadata(artifact_type, template_file)

        # Resolve output path
        resolved_output_path = self._resolve_output_path(artifact_type, output_path, context)

        # For legacy compatibility during migration: copy 'name' to 'dto_name'
        if artifact_type == "dto" and "name" in context and "dto_name" not in context:
            context["dto_name"] = context["name"]

        # Build dynamic model (user-facing schema) to validate input
        user_model = self._build_dynamic_model(artifact_type, artifact, BaseContext)

        # Validate user input via dynamic Context schema
        try:
            # LifecycleMixin has validate_default=True.
            # Strip output_path from context as we will inject it.
            # Pydantic extra="forbid" is set, so we must also strip any other extra fields
            # (like 'name' if not defined in the dynamic model fields list).
            _lifecycle_fields = {"output_path", "scaffold_created", "template_id", "version_hash"}
            if user_model.model_config.get("extra") == "allow":
                user_context = {k: v for k, v in context.items() if k not in _lifecycle_fields}
            else:
                allowed_fields = set(user_model.model_fields.keys()) - _lifecycle_fields
                user_context = {k: v for k, v in context.items() if k in allowed_fields}

            context_instance = user_model(**user_context)
        except Exception as e:
            from pydantic import ValidationError as PydanticValidationError  # noqa: PLC0415

            missing_fields = []
            msg_details = str(e)
            if isinstance(e, PydanticValidationError):
                for err in e.errors():
                    if err.get("type") == "missing":
                        loc_path = ".".join(str(x) for x in err["loc"])
                        missing_fields.append(loc_path)
                msg_details = ", ".join(
                    f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()
                )

            val_err = ValidationError(
                f"Failed to validate {artifact_type} context: {msg_details}",
                schema=self.get_context_schema(artifact_type),
                error_code="ERR_VALIDATION",
                params={"artifact_type": artifact_type, "error_details": str(e)},
            )
            val_err.missing = missing_fields
            val_err.provided = [k for k in context if k not in missing_fields]
            raise val_err from e

        # 2. Enrich to RenderContext (adds lifecycle fields)
        # We call _enrich_schema_context which is spied on by tests!
        render_context = self._enrich_schema_context(
            cast(BaseContext, context_instance),
            artifact_type,
            provided_output_path=resolved_output_path,
        )

        # 3. Update version_hash in render_context
        # Recreate with updated version_hash
        render_context_dict = render_context.model_dump()
        render_context_dict["version_hash"] = version_hash
        render_context = type(render_context).model_validate(render_context_dict)

        # Convert RenderContext to dict for scaffolder
        enriched_context = render_context.model_dump()

        # Format Path and datetime to string for template rendering and backward compatibility
        if "output_path" in enriched_context and enriched_context["output_path"] is not None:
            enriched_context["output_path"] = str(enriched_context["output_path"])
        if "scaffold_created" in enriched_context and isinstance(
            enriched_context["scaffold_created"], datetime
        ):
            enriched_context["scaffold_created"] = enriched_context["scaffold_created"].strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        # Check if schema-specific template exists (e.g., dto_v2.py.jinja2)
        # If not, use base template (backward compatibility)
        v2_template_file = template_file.replace(".py.jinja2", "_v2.py.jinja2")
        template_root = self._get_template_root()
        v2_template_path = template_root / v2_template_file
        v2_template_exists = v2_template_path.exists()

        if v2_template_exists:
            template_file = v2_template_file
            logger.info("Schema pipeline: Using template %s", v2_template_file)
            enriched_context["template_name"] = v2_template_file
        else:
            logger.info(
                "Schema pipeline: template not found (%s), using template %s",
                v2_template_file,
                template_file,
            )

        # Restore 'name' for _resolve_output_path downstream compatibility (if needed)
        if "name" in context and "name" not in enriched_context:
            enriched_context["name"] = context["name"]

        # Scaffold artifact with enriched context
        scaffold_kwargs = {k: v for k, v in enriched_context.items() if k != "artifact_type"}
        try:
            result = self.scaffolder.scaffold(
                artifact_type,
                skip_validation=True,  # Always True since we validated using dynamic Pydantic model
                note_context=note_context,
                **scaffold_kwargs,
            )
        except ValidationError as exc:
            if note_context is not None:
                note_context.produce(
                    Note(key="scaffold_validation_failed", params={"error_details": str(exc)})
                )
                note_context.produce(
                    Note(
                        key="scaffold_fields_recovery",
                        params={"artifact_type": artifact_type},
                    )
                )
            raise

        # Persist provenance to template registry
        self._persist_provenance(artifact_type, version_hash, template_file, tier_chain)

        # Validate and write
        return await self._validate_and_write(
            artifact_type, resolved_output_path, result.content, explicit=output_path is not None
        )

    def validate_artifact(self, artifact_type: str, **kwargs: Any) -> bool:  # noqa: ANN401
        """Validate artifact without scaffolding.

        Args:
            artifact_type: Artifact type_id from registry
            **kwargs: Template rendering context

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails
        """
        return self.scaffolder.validate(artifact_type, **kwargs)

    def get_artifact_path(self, artifact_type: str, name: str) -> Path:
        """Get full path for artifact.

        Args:
            artifact_type: Artifact type_id from registry
            name: Artifact name (without suffix/extension)

        Returns:
            Absolute path to artifact file (workspace_root / base_dir / filename)

        Raises:
            ConfigError: If no valid directory found
        """
        # Get artifact definition
        artifact = self.registry.get_artifact(artifact_type)

        # Find directories that allow this artifact type.
        # When no resolver was injected, construct one lazily so patch-based tests
        # can intercept DirectoryPolicyResolver() and legacy callers still work.
        if self._project_structure_config is None:
            raise ConfigError(
                "ProjectStructureConfig must be injected to resolve artifact directories",
                file_path="config/project_structure.yaml",
            )
        resolver = DirectoryPolicyResolver(self._project_structure_config)
        valid_dirs = resolver.find_directories_for_artifact(artifact_type)

        if not valid_dirs:
            raise ConfigError(
                f"No valid directory found for artifact type: {artifact_type}",
                file_path="config/project_structure.yaml",
            )

        # Use first directory
        base_dir = valid_dirs[0]

        # Construct filename: name + suffix + extension
        suffix = artifact.name_suffix or ""
        extension = artifact.file_extension
        file_name = f"{name}{suffix}{extension}"

        # Return absolute path: workspace_root / base_dir / filename
        if self.workspace_root is None:
            raise ConfigError(
                "workspace_root not configured - cannot resolve artifact paths automatically",
            )
        return self.workspace_root / base_dir / file_name

    def get_context_schema(self, artifact_type: str) -> dict[str, Any]:
        """Return JSON Schema dict for the context parameter of a schema-typed artifact type.

        Args:
            artifact_type: Artifact type id (e.g. 'research', 'dto')

        Returns:
            JSON Schema dict (Draft 7, $refs inlined via resolve_schema_refs)

        Raises:
            ConfigError: If artifact_type has no Context class registered
        """
        from mcp_server.utils.schema_utils import resolve_schema_refs  # noqa: PLC0415

        artifact = self.registry.get_artifact(artifact_type)
        if not artifact.context_schema:
            raise ConfigError(f"No Context schema defined for artifact type '{artifact_type}'.")

        dynamic_model = self._build_dynamic_model(artifact_type, artifact, BaseContext)
        return resolve_schema_refs(dynamic_model.model_json_schema())
