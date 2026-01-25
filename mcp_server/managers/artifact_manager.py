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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.version_hash import compute_version_hash
from mcp_server.validation.template_analyzer import TemplateAnalyzer
from mcp_server.validation.validation_service import ValidationService

logger = logging.getLogger(__name__)


class ArtifactManager:
    """Manages artifact scaffolding operations.

    NOT a singleton - each tool instantiates its own manager.
    Provides dependency injection for all collaborators.
    """

    def __init__(
        self,
        registry: ArtifactRegistryConfig | None = None,
        scaffolder: TemplateScaffolder | None = None,
        validation_service: ValidationService | None = None,
        fs_adapter: FilesystemAdapter | None = None,
        template_registry: Any | None = None,  # TemplateRegistry - late import to avoid circular
        **kwargs: Any,
    ) -> None:
        """Initialize manager with optional dependencies.

        Note:
            The test harness and some callers may pass a legacy/compat keyword
            argument `workspace_root`. When provided and fs_adapter is not passed,
            this is used to scope the default FilesystemAdapter.

        Args:
            registry: Artifact registry (default: singleton from file)
            scaffolder: Template scaffolder (default: new instance)
            validation_service: Validation service (default: new instance)
            fs_adapter: Filesystem adapter (default: new instance)
            template_registry: Template version registry (Task 1.1c - optional)
        """
        workspace_root = kwargs.pop("workspace_root", None)
        if kwargs:
            unexpected = ", ".join(sorted(kwargs.keys()))
            raise TypeError(f"Unexpected keyword arguments: {unexpected}")

        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None

        if registry is None and scaffolder is not None:
            maybe_registry = getattr(scaffolder, "registry", None)
            if isinstance(maybe_registry, ArtifactRegistryConfig):
                registry = maybe_registry

        self.registry = registry or ArtifactRegistryConfig.from_file()
        self.scaffolder = scaffolder or TemplateScaffolder(registry=self.registry)
        self.validation_service = validation_service or ValidationService()

        if fs_adapter is None and self.workspace_root is not None:
            fs_adapter = FilesystemAdapter(root_path=str(self.workspace_root))
        self.fs_adapter = fs_adapter or FilesystemAdapter()
        
        # Task 1.1c: Template registry for provenance (lazy init if not provided)
        self.template_registry = template_registry

    def _enrich_context(
        self, artifact_type: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Enrich template context with scaffold metadata fields.

        Adds metadata fields to support template-embedded metadata headers:
        - template_id: Artifact type identifier
        - scaffold_created: ISO 8601 UTC timestamp with Z suffix
        - output_path: File path (conditional - only for file artifacts)
        
        NOTE (Task 1.5b): Version comes from registry hash (version_hash field),
        not from artifacts.yaml. Version is injected separately in scaffold_artifact()
        before rendering (see Task 1.1c).

        Args:
            artifact_type: Artifact type_id from registry
            context: Original template rendering context

        Returns:
            Enriched context dict (preserves original + adds metadata)
        """
        # Get artifact definition to read output_type
        artifact = self.registry.get_artifact(artifact_type)

        # Create enriched context (copy original to preserve)
        enriched = dict(context)

        # Add metadata fields
        enriched["template_id"] = artifact_type

        # Determine format from file extension (for SCAFFOLD comment syntax)
        extension = artifact.file_extension
        if extension in [".py"]:
            enriched["format"] = "python"
        elif extension in [".yaml", ".yml"]:
            enriched["format"] = "yaml"
        elif extension in [".sh", ".bash"]:
            enriched["format"] = "shell"
        elif extension in [".md"]:
            enriched["format"] = "markdown"
        else:
            enriched["format"] = "python"  # Default to Python comment style

        # Generate ISO 8601 UTC timestamp with Z suffix
        now_utc = datetime.now(timezone.utc)
        enriched["scaffold_created"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Conditionally add output_path for file artifacts only
        if artifact.output_type == "file":
            if "output_path" in context:
                # Use explicitly provided output_path (test override, explicit path)
                enriched["output_path"] = context["output_path"]
            else:
                # Resolve output path via get_artifact_path() (auto-resolution)
                name = context.get("name", "unnamed")
                artifact_path = self.get_artifact_path(artifact_type, name)
                enriched["output_path"] = str(artifact_path)

        return enriched

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
            parent = Path(__file__).parent.parent
            template_root = parent / "scaffolding" / "templates"
            
            # Initialize analyzer
            analyzer = TemplateAnalyzer(template_root=template_root)
            
            # Get full inheritance chain
            template_path = template_root / template_file
            if not template_path.exists():
                logger.warning(f"Template not found for tier extraction: {template_file}")
                return []
            
            chain_paths = analyzer.get_inheritance_chain(template_path)
            
            # Extract (template_name, version) from TEMPLATE_METADATA in each template
            tier_chain: list[tuple[str, str]] = []
            for path in chain_paths:
                # Read template content to extract TEMPLATE_METADATA
                try:
                    template_content = path.read_text(encoding="utf-8")
                    metadata = analyzer.extract_metadata(template_content)
                    
                    # Get template name (stem without .jinja2 suffix)
                    template_name = path.stem
                    
                    # Get version from metadata (default to "1.0" if missing)
                    version = metadata.get("version", "1.0") if metadata else "1.0"
                    
                    tier_chain.append((template_name, version))
                    
                except Exception as e:
                    # Log but continue - use fallback for this template
                    logger.warning(f"Failed to read metadata from {path}: {e}")
                    template_name = path.stem
                    tier_chain.append((template_name, "1.0"))
            
            return tier_chain
            
        except Exception as e:
            # Pragmatic: log and return empty list (don't block scaffolding)
            logger.warning(f"Failed to extract tier chain for {template_file}: {e}")
            return []

    def _build_tier_versions_dict(
        self,
        template_file: str,
        tier_chain: list[tuple[str, str]]
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
            parent = Path(__file__).parent.parent
            template_root = parent / "scaffolding" / "templates"
            analyzer = TemplateAnalyzer(template_root=template_root)
            
            template_path = template_root / template_file
            if not template_path.exists():
                return {}
            
            chain_paths = analyzer.get_inheritance_chain(template_path)
            
            # Map each path to its tier and combine with version from tier_chain
            for idx, path in enumerate(chain_paths):
                if idx >= len(tier_chain):
                    break
                    
                relative = path.relative_to(template_root)
                parts = relative.parts
                
                # Determine tier from path structure
                if len(parts) >= 2 and parts[0] in ("concrete", "tier0", "tier1", "tier2", "tier3"):
                    tier = parts[0]
                elif len(parts) == 1:
                    # Top-level template (unlikely but handle gracefully)
                    tier = "tier0"
                else:
                    # Unknown structure - skip
                    continue
                
                template_name, version = tier_chain[idx]
                tier_versions[tier] = (template_name, version)
                
        except Exception as e:
            logger.warning(f"Failed to build tier_versions dict: {e}")
            
        return tier_versions

    async def scaffold_artifact(
        self,
        artifact_type: str,
        output_path: str | None = None,
        **context: Any
    ) -> str:
        """Scaffold artifact from template and write to file.

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

        # Task 1.1c: Compute version_hash before rendering (for SCAFFOLD header)
        artifact = self.registry.get_artifact(artifact_type)
        template_file = artifact.template_path
        
        # QA-2: Fail-fast if template_path is null (not yet implemented)
        if template_file is None:
            raise ConfigError(
                f"Artifact type '{artifact_type}' has no template configured (template_path=null). "
                f"This artifact type is not yet implemented."
            )
        
        # QA-4: Extract real tier chain via introspection (replaces placeholder)
        tier_chain = self._extract_tier_chain(template_file)
        
        # Compute version hash
        version_hash = compute_version_hash(
            artifact_type=artifact_type,
            template_file=template_file or "",
            tier_chain=tier_chain
        )
        
        # Generate timestamp for SCAFFOLD header
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Inject SCAFFOLD metadata into context (Task 1.1c)
        context = {
            **context,
            "artifact_type": artifact_type,
            "version_hash": version_hash,
            "timestamp": timestamp,
        }

        # 1. Enrich context with metadata fields
        enriched_context = self._enrich_context(artifact_type, context)

        # 2. Scaffold artifact with enriched context
        # NOTE: artifact_type is passed as positional arg, so remove from kwargs to avoid duplicate
        scaffold_kwargs = {k: v for k, v in enriched_context.items() if k != "artifact_type"}
        result = self.scaffolder.scaffold(artifact_type, **scaffold_kwargs)

        # 3. Get artifact definition to determine validation policy
        artifact = self.registry.get_artifact(artifact_type)
        
        # Task 1.1c: Save to registry for provenance tracking
        if self.template_registry is not None:
            # Build tier_versions dict with real versions from TEMPLATE_METADATA
            # Uses _build_tier_versions_dict to map tier names to (template_id, version)
            tier_versions = self._build_tier_versions_dict(template_file, tier_chain)
            
            self.template_registry.save_version(
                artifact_type=artifact_type,
                version_hash=version_hash,
                tier_versions=tier_versions
            )

        # 4. Resolve output path (needed for path-based validation)
        if output_path is None:
            # Handle generic type special case
            if artifact_type == "generic":
                # Generic type requires explicit output_path in context
                if "output_path" not in enriched_context:
                    raise ValidationError(
                        "Generic artifacts require explicit output_path in context",
                        hints=[
                            "Add output_path to context: "
                            "context={'output_path': 'path/to/file.py', ...}",
                            "Generic artifacts can be placed anywhere"
                        ]
                    )
                output_path = enriched_context["output_path"]
            else:
                # Regular types: auto-resolve via get_artifact_path
                name = enriched_context.get("name", "unnamed")
                artifact_path = self.get_artifact_path(artifact_type, name)
                output_path = str(artifact_path)

        assert output_path is not None, "output_path should be set by this point"

        # 5. Validate rendered content using full validator chain (DoD requirement)
        # Use validate() to invoke registered validators (PythonSyntaxValidator, MarkdownValidator)
        passed, issues = await self.validation_service.validate(
            output_path, result.content
        )

        if not passed:
            if artifact.type == "code":
                # BLOCK policy: Code artifacts must pass validation
                raise ValidationError(
                    f"Generated {artifact_type} artifact failed validation:\n{issues}",
                    hints=[
                        "Check template for syntax errors",
                        "Verify template variables are correctly substituted"
                    ]
                )

            # WARN policy: Doc artifacts emit warning but continue
            logger.warning(
                "Validation issues in %s artifact (type=%s), writing anyway:\n%s",
                artifact_type,
                artifact.type,
                issues
            )

        # 6. Handle ephemeral vs file artifacts
        if artifact.output_type == "ephemeral":
            # Ephemeral artifacts: write to temp file (consistent with Issue #121)
            # Enables: ScaffoldEdit operations, validation, agent fill cycle
            temp_dir = Path(".st3/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique temp filename with correct extension
            ext = artifact.file_extension  # .txt, .md, etc
            temp_filename = f"{artifact_type}_{uuid.uuid4().hex[:8]}{ext}"
            temp_path = temp_dir / temp_filename

            # Write temp file with scaffolded content
            temp_path.write_text(result.content, encoding="utf-8")
            return str(temp_path)
        # File artifacts: write to disk and return path
        self.fs_adapter.write_file(output_path, result.content)
        return str(self.fs_adapter.resolve_path(output_path))

    def validate_artifact(
        self, artifact_type: str, **kwargs: Any
    ) -> bool:
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

    def get_artifact_path(
        self, artifact_type: str, name: str
    ) -> Path:
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

        # Find directories that allow this artifact type
        resolver = DirectoryPolicyResolver()
        valid_dirs = resolver.find_directories_for_artifact(artifact_type)

        if not valid_dirs:
            raise ConfigError(
                f"No valid directory found for artifact type: {artifact_type}",
                file_path=".st3/project_structure.yaml"
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
                hints=[
                    "Option 1: Initialize ArtifactManager with workspace_root "
                    "parameter: ArtifactManager(workspace_root='/path/to/workspace')",
                    "Option 2: Provide explicit output_path in "
                    "scaffold_artifact() call",
                    "Option 3: For MCP tools, workspace_root should be passed "
                    "from server initialization"
                ]
            )
        return self.workspace_root / base_dir / file_name
