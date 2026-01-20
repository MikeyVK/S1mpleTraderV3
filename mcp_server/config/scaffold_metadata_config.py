"""
Configuration models for scaffold metadata system.

Loads and validates .st3/scaffold_metadata.yaml which defines:
- Comment patterns for different file types (hash, double_slash, etc.)
- Metadata field definitions with validation regex

Used by ScaffoldMetadataParser to detect and validate SCAFFOLD comments.
"""

import yaml
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class CommentPattern(BaseModel):
    """
    Defines how to detect SCAFFOLD metadata in a specific comment syntax.
    
    Example:
        CommentPattern(
            syntax="hash",
            prefix=r"#\\s*",
            metadata_line_regex=r"^#\\s*SCAFFOLD:\\s*(.+)$"
        )
    """
    
    syntax: Literal["hash", "double_slash", "html_comment", "jinja_comment"] = Field(
        description="Comment syntax identifier"
    )
    prefix: str = Field(
        min_length=1,
        description="Regex pattern matching comment prefix"
    )
    metadata_line_regex: str = Field(
        min_length=1,
        description="Regex pattern matching full metadata line"
    )


class MetadataField(BaseModel):
    """
    Defines a metadata field with validation rules.
    
    Example:
        MetadataField(
            name="template",
            format_regex=r"^[a-z0-9_-]+$",
            required=True
        )
    """
    
    name: str = Field(
        min_length=1,
        description="Field name (e.g., 'template', 'version')"
    )
    format_regex: str = Field(
        min_length=1,
        description="Regex pattern for field value validation"
    )
    required: bool = Field(
        description="Whether field must be present"
    )


class ScaffoldMetadataConfig(BaseModel):
    """
    Main configuration model for scaffold metadata system.
    
    Loaded from .st3/scaffold_metadata.yaml.
    """
    
    comment_patterns: list[CommentPattern] = Field(
        min_length=1,
        description="Supported comment syntaxes"
    )
    metadata_fields: list[MetadataField] = Field(
        min_length=1,
        description="Metadata field definitions"
    )
    
    @classmethod
    def from_file(cls, path: Optional[Path] = None) -> "ScaffoldMetadataConfig":
        """
        Load configuration from YAML file.
        
        Args:
            path: Path to config file. Defaults to .st3/scaffold_metadata.yaml
        
        Returns:
            Validated configuration
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValidationError: If config doesn't match schema
        """
        if path is None:
            path = Path(".st3/scaffold_metadata.yaml")
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(**data)
    
    def get_pattern(self, syntax: str) -> Optional[CommentPattern]:
        """
        Retrieve comment pattern by syntax identifier.
        
        Args:
            syntax: Syntax identifier (e.g., "hash", "double_slash")
        
        Returns:
            Matching pattern or None if not found
        """
        for pattern in self.comment_patterns:
            if pattern.syntax == syntax:
                return pattern
        return None
    
    def get_field(self, name: str) -> Optional[MetadataField]:
        """
        Retrieve metadata field definition by name.
        
        Args:
            name: Field name (e.g., "template", "path")
        
        Returns:
            Matching field or None if not found
        """
        for field in self.metadata_fields:
            if field.name == name:
                return field
        return None
