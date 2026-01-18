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

from pathlib import Path
from typing import Any

from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.validation.validation_service import ValidationService


class ArtifactManager:
    """Manages artifact scaffolding operations.

    NOT a singleton - each tool instantiates its own manager.
    Provides dependency injection for all collaborators.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        workspace_root: Path | None = None,
        registry: ArtifactRegistryConfig | None = None,
        scaffolder: TemplateScaffolder | None = None,
        validation_service: ValidationService | None = None,
        fs_adapter: FilesystemAdapter | None = None
    ) -> None:
        """Initialize manager with optional dependencies.

        Args:
            workspace_root: Project root directory (default: cwd)
            registry: Artifact registry (default: singleton from file)
            scaffolder: Template scaffolder (default: new instance)
            validation_service: Validation service (default: new instance)
            fs_adapter: Filesystem adapter (default: new instance)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.registry = registry or ArtifactRegistryConfig.from_file()
        self.scaffolder = scaffolder or TemplateScaffolder(registry=self.registry)
        self.validation_service = validation_service or ValidationService()
        self.fs_adapter = fs_adapter or FilesystemAdapter()

    def scaffold_artifact(
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
            ValidationError: If validation fails or artifact_type unknown
            ConfigError: If template not found
        """
        # 1. Scaffold artifact
        result = self.scaffolder.scaffold(artifact_type, **context)

        # 2. Validate rendered content (D10 - delegate to ValidationService)
        passed, issues = self.validation_service.validate_content(
            result.content, artifact_type
        )
        if not passed:
            raise ValidationError(
                f"Generated {artifact_type} artifact failed validation:\n{issues}",
                hints=[
                    "Check template for syntax errors",
                    "Verify template variables are correctly substituted"
                ]
            )

        # 3. Resolve output path
        if output_path is None:
            # Gap 3 fix: Handle generic type special case
            if artifact_type == "generic":
                # Generic type requires explicit output_path in context
                if "output_path" not in context:
                    raise ValidationError(
                        "Generic artifacts require explicit output_path in context",
                        hints=[
                            "Add output_path to context: "
                            "context={'output_path': 'path/to/file.py', ...}",
                            "Generic artifacts can be placed anywhere"
                        ]
                    )
                output_path = context["output_path"]
            else:
                # Regular types: auto-resolve via get_artifact_path (D2)
                name = context.get("name", "unnamed")
                artifact_path = self.get_artifact_path(artifact_type, name)
                output_path = str(artifact_path)

        # 4. Write file to filesystem (Gap 1 fix - CRITICAL)
        assert output_path is not None, "output_path should be set by this point"
        self.fs_adapter.write_file(output_path, result.content)

        # Return absolute path to created file
        # Note: We call _validate_path to get the absolute path
        # This is acceptable as it's a utility method, not business logic
        full_path = self.fs_adapter._validate_path(output_path)  # pylint: disable=protected-access
        return str(full_path)

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
        """Get full path for artifact (Cycle 8).

        Args:
            artifact_type: Artifact type_id from registry
            name: Artifact name (without suffix/extension)

        Returns:
            Full path to artifact file

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

        # Return full path
        return self.workspace_root / base_dir / file_name
