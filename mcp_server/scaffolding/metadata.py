"""
Metadata parser for scaffolded files.

Parses SCAFFOLD comments from the first line of generated files to extract:
- template: Template ID used
- version: Template version
- created: Creation timestamp
- updated: Last update timestamp (optional)
- path: File path (optional for ephemeral artifacts)
"""

import re
from pathlib import Path
from typing import Optional

from mcp_server.config.scaffold_metadata_config import ScaffoldMetadataConfig


class MetadataParseError(Exception):
    """Raised when metadata parsing fails validation."""

    pass


class ScaffoldMetadataParser:
    """
    Parses SCAFFOLD metadata from first line of scaffolded files.

    Example:
        >>> parser = ScaffoldMetadataParser()
        >>> content = "# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z\\n..."
        >>> metadata = parser.parse(content, ".py")
        >>> metadata["template"]
        'dto'
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize parser with configuration.

        Args:
            config_path: Path to config file (defaults to .st3/scaffold_metadata.yaml)
        """
        self.config = ScaffoldMetadataConfig.from_file(config_path)

    def parse(self, content: str, extension: str) -> Optional[dict[str, str]]:
        """
        Parse metadata from file content.

        Args:
            content: File content to parse
            extension: File extension (e.g., ".py", ".ts")

        Returns:
            Metadata dict or None if not a scaffolded file

        Raises:
            MetadataParseError: If metadata is invalid
        """
        if not content:
            return None

        # Get first line
        first_line = content.split("\n")[0].strip()
        if not first_line:
            return None

        # Find matching pattern for extension
        pattern = None
        for comment_pattern in self.config.comment_patterns:
            if extension in [".py", ".yaml", ".sh", ".txt"] and comment_pattern.syntax == "hash":
                pattern = comment_pattern
                break
            elif extension in [".ts", ".js", ".java", ".cs"] and comment_pattern.syntax == "double_slash":
                pattern = comment_pattern
                break
            elif extension in [".md", ".html", ".xml"] and comment_pattern.syntax == "html_comment":
                pattern = comment_pattern
                break
            elif extension in [".jinja2", ".j2"] and comment_pattern.syntax == "jinja_comment":
                pattern = comment_pattern
                break

        if not pattern:
            return None

        # Check if first line matches SCAFFOLD pattern
        match = re.match(pattern.metadata_line_regex, first_line)
        if not match:
            return None

        # Extract metadata string
        metadata_str = match.group(1).strip()

        # Parse key=value pairs
        metadata = self._parse_key_value_pairs(metadata_str)

        # Validate metadata
        self._validate_metadata(metadata)

        return metadata

    def _parse_key_value_pairs(self, metadata_str: str) -> dict[str, str]:
        """
        Parse key=value pairs from metadata string.

        Args:
            metadata_str: String like "template=dto version=1.0 created=..."

        Returns:
            Dict of parsed key-value pairs

        Raises:
            MetadataParseError: If key=value format is invalid
        """
        metadata = {}
        # Use regex to split on whitespace but keep values together
        # Pattern: key=value pairs separated by spaces
        pattern = r'(\w+)=([^\s]+)'
        matches = re.findall(pattern, metadata_str)

        if not matches:
            raise MetadataParseError(f"No valid key=value pairs found in: {metadata_str}")

        for key, value in matches:
            metadata[key] = value

        return metadata

    def _validate_metadata(self, metadata: dict[str, str]) -> None:
        """
        Validate metadata against config schema.

        Args:
            metadata: Parsed metadata dict

        Raises:
            MetadataParseError: If validation fails
        """
        # Check required fields
        for field_def in self.config.metadata_fields:
            if field_def.required and field_def.name not in metadata:
                raise MetadataParseError(f"Missing required field: {field_def.name}")

        # Filter to known fields only and validate
        validated = {}
        for field_name, field_value in metadata.items():
            field_def = self.config.get_field(field_name)

            # Skip unknown fields (silently ignored)
            if not field_def:
                continue

            # Validate against regex
            if not re.match(field_def.format_regex, field_value):
                raise MetadataParseError(
                    f"Invalid value '{field_value}' for field '{field_name}'. "
                    f"Expected pattern: {field_def.format_regex}"
                )

            validated[field_name] = field_value

        # Replace metadata with validated subset
        metadata.clear()
        metadata.update(validated)
