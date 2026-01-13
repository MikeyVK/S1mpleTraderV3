"""Component registry configuration model.

Purpose: Load and validate components.yaml
Domain: WAT (what can be scaffolded)
Cross-references: None (leaf config)
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator

from mcp_server.core.errors import ConfigError


class ComponentDefinition(BaseModel):
    """Single component type definition."""
    
    type_id: str = Field(
        ..., 
        description="Component type identifier (dto, worker, etc.)"
    )
    description: str = Field(
        ..., 
        description="Human-readable description of component purpose"
    )
    scaffolder_class: str = Field(
        ..., 
        description="Scaffolder class name for dynamic loading (e.g., 'DTOScaffolder')"
    )
    scaffolder_module: str = Field(
        ..., 
        description="Module path for scaffolder class (e.g., 'mcp_server.scaffolders.dto_scaffolder')"
    )
    template_path: Optional[str] = Field(
        None, 
        description="Path to Jinja2 template (relative to workspace root)"
    )
    fallback_template: Optional[str] = Field(
        None, 
        description="Fallback template if primary template not found (DRY for Issue #107)"
    )
    name_suffix: Optional[str] = Field(
        None, 
        description="Auto-append suffix if missing (e.g., 'Worker' for workers) - Issue #107"
    )
    base_path: Optional[str] = Field(
        None, 
        description="Default output directory for this component type"
    )
    test_base_path: Optional[str] = Field(
        None, 
        description="Default test directory for this component type"
    )
    generate_test: bool = Field(
        True, 
        description="Whether to generate test file by default"
    )
    required_fields: List[str] = Field(
        default_factory=list, 
        description="Mandatory scaffold parameters"
    )
    optional_fields: List[str] = Field(
        default_factory=list, 
        description="Optional scaffold parameters"
    )


class ComponentRegistryConfig(BaseModel):
    """Component registry configuration (WAT domain).
    
    Purpose: Single source of truth for component type definitions
    Loaded from: .st3/components.yaml
    Used by: ScaffoldComponentTool, DirectoryPolicyResolver (indirect)
    """
    
    components: Dict[str, ComponentDefinition] = Field(
        ...,
        description="Component type definitions keyed by type_id"
    )
    
    # Singleton pattern
    _instance: Optional["ComponentRegistryConfig"] = None
    
    @classmethod
    def from_file(
        cls, 
        config_path: str = ".st3/components.yaml"
    ) -> "ComponentRegistryConfig":
        """Load config from YAML file (singleton pattern).
        
        Args:
            config_path: Path to components.yaml file
            
        Returns:
            Singleton instance of ComponentRegistryConfig
            
        Raises:
            ConfigError: If file not found or YAML invalid
        """
        # Return cached instance if exists
        if cls._instance is not None:
            return cls._instance
        
        # Load and parse YAML
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(
                f"Config file not found: {config_path}",
                file_path=config_path
            )
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {config_path}: {e}",
                file_path=config_path
            )
        
        # Validate structure
        if "component_types" not in data:
            raise ConfigError(
                f"Missing 'component_types' key in {config_path}",
                file_path=config_path
            )
        
        # Transform to ComponentDefinition instances
        components = {}
        for type_id, comp_data in data["component_types"].items():
            try:
                # Add type_id to data
                comp_data_with_id = {"type_id": type_id, **comp_data}
                components[type_id] = ComponentDefinition(**comp_data_with_id)
            except Exception as e:
                raise ConfigError(
                    f"Invalid component definition for '{type_id}': {e}",
                    file_path=config_path
                )
        
        # Create and cache instance
        cls._instance = cls(components=components)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing only)."""
        cls._instance = None
