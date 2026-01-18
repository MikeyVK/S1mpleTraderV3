"""ArtifactManager orchestrates artifact scaffolding (Cycles 7-8).

Manager pattern - NOT singleton, instantiated per tool.
Delegates to TemplateScaffolder for actual scaffolding.
"""

from pathlib import Path
from typing import Any

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.directory_policy_resolver import DirectoryPolicyResolver
from mcp_server.core.errors import ConfigError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder


class ArtifactManager:
    """Manages artifact scaffolding operations.

    NOT a singleton - each tool instantiates its own manager.
    Provides dependency injection for all collaborators.
    """

    def __init__(
        self,
        workspace_root: Path | None = None,
        registry: ArtifactRegistryConfig | None = None,
        scaffolder: TemplateScaffolder | None = None
    ) -> None:
        """Initialize manager with optional dependencies.

        Args:
            workspace_root: Project root directory (default: cwd)
            registry: Artifact registry (default: singleton from file)
            scaffolder: Template scaffolder (default: new instance)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.registry = registry or ArtifactRegistryConfig.from_file()
        self.scaffolder = scaffolder or TemplateScaffolder(registry=self.registry)

    def scaffold_artifact(
        self, artifact_type: str, **kwargs: Any
    ) -> str:
        """Scaffold artifact from template.

        Args:
            artifact_type: Artifact type_id from registry
            **kwargs: Template rendering context

        Returns:
            Path to scaffolded artifact (relative to workspace_root)

        Raises:
            ValidationError: If validation fails
            ConfigError: If template not found
        """
        # Delegate to scaffolder
        result = self.scaffolder.scaffold(artifact_type, **kwargs)

        # For now, just return filename (Cycle 8 adds path resolution)
        return result.file_name if result.file_name else "unknown.txt"

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
