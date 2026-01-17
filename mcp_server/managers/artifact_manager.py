"""ArtifactManager orchestrates artifact scaffolding (Cycle 7).

Manager pattern - NOT singleton, instantiated per tool.
Delegates to TemplateScaffolder for actual scaffolding.
"""

from pathlib import Path
from typing import Any

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
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
        return result.file_name
    
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
