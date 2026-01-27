"""
Metadata parser for scaffolded files.

Parses 2-line SCAFFOLD metadata from generated files (Issue #72 format):
Line 1: # filepath or <!-- filepath -->
Line 2: # template=dto version=abc12345 created=2026-01-27T10:00Z updated=

- template: Template ID used
- version: Template version hash (8 hex chars)
- created: Creation timestamp (ISO 8601 UTC)
- updated: Last update timestamp (optional, can be empty)
"""

import re
from pathlib import Path
from typing import Optional

from mcp_server.config.scaffold_metadata_config import (
    CommentPattern,
    MetadataField,
    ScaffoldMetadataConfig,
)
from mcp_server.core.exceptions import MetadataParseError


class ScaffoldMetadataParser:  # pylint: disable=too-few-public-methods
    """
    Parses 2-line SCAFFOLD metadata from scaffolded files (Issue #72 format).

    NEW FORMAT (no "SCAFFOLD:" prefix):
    Line 1: # backend/dtos/user_dto.py
    Line 2: # template=dto version=abc12345 created=2026-01-27T10:00Z updated=

    Example:
        >>> parser = ScaffoldMetadataParser()
        >>> content = "# backend/dtos/user_dto.py\\n# template=dto version=abc12345 created=2026-01-27T10:00Z updated=\\n..."
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

    def _filter_patterns(self, extension: str) -> list[CommentPattern]:
        """
        Filter comment patterns by file extension.

        Args:
            extension: File extension (e.g., ".py", ".ts")

        Returns:
            List of CommentPattern objects matching the extension
        """
        return [
            pattern
            for pattern in self.config.comment_patterns
            if extension in pattern.extensions
        ]

    def parse(self, content: str, extension: str) -> Optional[dict[str, str]]:
        """
        Parse 2-line metadata from file content (Issue #72 format).

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

        # Get first 2 lines
        lines = content.split("\n")
        if len(lines) < 2:
            return None

        first_line = lines[0].strip()
        second_line = lines[1].strip()

        if not first_line or not second_line:
            return None

        # Filter patterns by extension
        patterns = self._filter_patterns(extension)
        if not patterns:
            return None  # Unknown extension

        # Try each matching pattern
        for pattern in patterns:
            # NEW: Check line 2 for metadata (not line 1)
            match = re.match(pattern.metadata_line_regex, second_line)
            if match:
                # Extract metadata string from line 2
                # No capturing group needed - whole line is metadata
                metadata_str = second_line

                # Remove comment prefix (e.g., "# " or "<!-- " or "// ")
                metadata_str = re.sub(pattern.prefix, "", metadata_str).strip()
                # Remove comment suffix for HTML/Jinja (e.g., " -->" or " #}")
                metadata_str = re.sub(r"\s*(-->|#\})$", "", metadata_str).strip()

                # Parse key=value pairs
                metadata = self._parse_key_value_pairs(metadata_str)

                # Validate metadata
                self._validate_metadata(metadata)

                return metadata

        # No pattern matched
        return None

    def _parse_key_value_pairs(self, metadata_str: str) -> dict[str, str]:
        """
        Parse key=value pairs from metadata string.

        Args:
            metadata_str: String like "template=dto version=abc12345 created=..."

        Returns:
            Dict of parsed key-value pairs

        Raises:
            MetadataParseError: If key=value format is invalid
        """
        metadata = {}
        # Use regex to split on whitespace but keep values together
        # Pattern: key=value pairs separated by spaces
        # Updated: Allow empty values (e.g., updated=)
        pattern = r'(\w+)=([^\s]*)'
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
        validated: dict[str, str] = {}
        for field_name, field_value in metadata.items():
            field_config: Optional[MetadataField] = self.config.get_field(field_name)

            # Skip unknown fields (silently ignored)
            if field_config is None:
                continue
            # Type narrowing: field_config is non-None past this point
            assert field_config is not None

            # Validate against regex
            if not re.match(field_config.format_regex, field_value):
                raise MetadataParseError(
                    f"Invalid value '{field_value}' for field '{field_name}'. "
                    f"Expected pattern: {field_config.format_regex}"
                )

            validated[field_name] = field_value

        # Replace metadata with validated subset
        metadata.clear()
        metadata.update(validated)
