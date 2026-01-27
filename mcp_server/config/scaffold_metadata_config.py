"""
Configuration models for scaffold metadata system.

Loads and validates .st3/scaffold_metadata.yaml which defines:
- Comment patterns for different file types (hash, double_slash, etc.)
- Metadata field definitions with validation regex

Used by ScaffoldMetadataParser to detect and validate SCAFFOLD comments.
"""

import re
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class ConfigError(Exception):
    """Custom exception for configuration errors with helpful hints."""

    def __init__(self, message: str, hint: Optional[str] = None):
        self.hint = hint
        super().__init__(f"{message}\n💡 {hint}" if hint else message)

class CommentPattern(BaseModel):
    """
    Defines how to detect 2-line SCAFFOLD metadata in a specific comment syntax.

    NEW FORMAT (Issue #72):
    Line 1: filepath only
    Line 2: metadata fields (template= version= created= updated=)

    Example:
        CommentPattern(
            syntax="hash",
            prefix=r"#\\s*",
            filepath_line_regex=r"^#\\s*(.+\\.py)$",
            metadata_line_regex=r"^#\\s*template=.+\\s+version=.+\\s+created=.+\\s+updated=.*$",
            extensions=[".py", ".yaml", ".sh"]
        )
    """

    syntax: Literal["hash", "double_slash", "html_comment", "jinja_comment"] = Field(
        description="Comment syntax identifier"
    )
    prefix: str = Field(
        min_length=1,
        description="Regex pattern matching comment prefix"
    )
    filepath_line_regex: str = Field(
        min_length=1,
        description="Regex pattern matching line 1 (filepath)"
    )
    metadata_line_regex: str = Field(
        min_length=1,
        description="Regex pattern matching line 2 (metadata)"
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="File extensions this pattern applies to (e.g., ['.py', '.yaml'])"
    )

    @field_validator("prefix", "filepath_line_regex", "metadata_line_regex")
    @classmethod
    def validate_regex_pattern(cls, v: str) -> str:
        """Ensure pattern is a valid compilable regex."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {v}\nError: {e}") from e
        return v


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

    @field_validator("format_regex")
    @classmethod
    def validate_regex_pattern(cls, v: str) -> str:
        """Ensure pattern is a valid compilable regex."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {v}\nError: {e}") from e
        return v


class ScaffoldMetadataConfig(BaseModel):
    """
    Main configuration model for scaffold metadata system.

    Loaded from .st3/scaffold_metadata.yaml.
    """

    version: str = Field(
        default="1.0",
        description="Config schema version for future migrations"
    )
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
            ConfigError: If config file is missing, invalid YAML, or validation fails
        """
        if path is None:
            path = Path(".st3/scaffold_metadata.yaml")

        if not path.exists():
            raise ConfigError(
                f"Config file not found: {path}",
                hint="Create .st3/scaffold_metadata.yaml with comment_patterns and metadata_fields"
            )

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {path}",
                hint=f"Check YAML syntax: {e}"
            ) from e

        try:
            return cls(**data)
        except Exception as e:
            raise ConfigError(
                f"Config validation failed for {path}",
                hint=f"Check schema compliance: {e}"
            ) from e

    def get_pattern(self, syntax: str) -> Optional[CommentPattern]:
        """
        Retrieve comment pattern by syntax identifier.

        Args:
            syntax: Syntax identifier (e.g., "hash", "double_slash")

        Returns:
            Matching pattern or None if not found

        Example:
            >>> config = ScaffoldMetadataConfig.from_file()
            >>> pattern = config.get_pattern("hash")
            >>> pattern.prefix
            '#\\\\s*'
        """
        return next(
            (p for p in self.comment_patterns if p.syntax == syntax),
            None
        )

    def get_field(self, name: str) -> Optional[MetadataField]:
        """
        Retrieve metadata field definition by name.

        Args:
            name: Field name (e.g., "template", "path")

        Returns:
            Matching field or None if not found

        Example:
            >>> config = ScaffoldMetadataConfig.from_file()
            >>> field = config.get_field("path")
            >>> field.required
            False
        """
        return next(
            (f for f in self.metadata_fields if f.name == name),
            None
        )
