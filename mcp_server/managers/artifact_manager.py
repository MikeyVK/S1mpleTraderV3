"""ArtifactManager orchestrates artifact scaffolding (Cycles 7-8).

Manager pattern - NOT singleton, instantiated per tool.
Delegates to TemplateScaffolder for actual scaffolding.
"""

from pathlib import Path
from typing import Any

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.errors import ConfigError, ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.validation.validation_service import ValidationService


class ArtifactManager:
    """Manages artifact scaffolding operations.

    NOT a singleton - each tool instantiates its own manager.
    Provides dependency injection for all collaborators.
    """

    def __init__(
        self,
        workspace_root: Path | None = None,
        registry: ArtifactRegistryConfig | None = None,
        scaffolder: TemplateScaffolder | None = None,
        validation_service: ValidationService | None = None
    ) -> None:
        """Initialize manager with optional dependencies.

        Args:
            workspace_root: Project root directory (default: cwd)
            registry: Artifact registry (default: singleton from file)
            scaffolder: Template scaffolder (default: new instance)
            validation_service: Validation service (default: new instance)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.registry = registry or ArtifactRegistryConfig.from_file()
        self.scaffolder = scaffolder or TemplateScaffolder(registry=self.registry)
        self.validation_service = validation_service or ValidationService()

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
        _result = self.scaffolder.scaffold(artifact_type, **context)  # noqa: F841

        # 2. Validate rendered content (D10 - delegate to ValidationService)
        # Note: ValidationService currently validates against templates,
        # we'll use it for architectural validation
        # For now, skip validation step as ValidationService needs to be updated
        # to support artifact content validation
        # TODO(Cycle 6): Add validation_service.validate_content(_result.content, artifact_type)

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

        # 4. For now, return the path (file writing will be added later)
        # TODO(Cycle 8): Write result.content to output_path using FilesystemAdapter
        # result variable will be used when file writing is implemented
        return output_path  # type: ignore[return-value]

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
