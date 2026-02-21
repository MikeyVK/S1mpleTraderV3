"""
Unit tests for scaffold metadata configuration models.

Tests the Pydantic models that load and validate .st3/scaffold_metadata.yaml.
Following TDD: These tests are written BEFORE implementation (RED phase).
"""

import pytest
from pydantic import ValidationError

from mcp_server.config.scaffold_metadata_config import (
    CommentPattern,
    ConfigError,
    MetadataField,
    ScaffoldMetadataConfig,
)


class TestCommentPattern:
    """Test comment pattern model validation."""

    def test_valid_hash_pattern(self):
        """RED: Hash pattern should validate (2-line format)."""
        pattern = CommentPattern(
            syntax="hash",
            prefix=r"#\s*",
            filepath_line_regex=r"^#\s*(.+\.py)$",
            metadata_line_regex=r"^#\s*template=.+\s+version=.+\s+created=.+\s+updated=.*$",
        )
        assert pattern.syntax == "hash"
        assert pattern.prefix == r"#\s*"

    def test_valid_double_slash_pattern(self):
        """RED: Double-slash pattern should validate (2-line format)."""
        pattern = CommentPattern(
            syntax="double_slash",
            prefix=r"//\s*",
            filepath_line_regex=r"^//\s*(.+\.ts)$",
            metadata_line_regex=r"^//\s*template=.+\s+version=.+\s+created=.+\s+updated=.*$",
        )
        assert pattern.syntax == "double_slash"

    def test_invalid_syntax_fails(self):
        """RED: Invalid syntax should raise ValidationError."""
        with pytest.raises(ValidationError):
            CommentPattern(
                syntax="invalid_syntax",  # type: ignore[arg-type]
                prefix="#",
                filepath_line_regex="^#.*$",
                metadata_line_regex="^#.*$",
            )

    def test_empty_prefix_fails(self):
        """RED: Empty prefix should fail validation."""
        with pytest.raises(ValidationError):
            CommentPattern(
                syntax="hash", prefix="", filepath_line_regex="^#.*$", metadata_line_regex="^#.*$"
            )

    def test_invalid_regex_pattern_fails(self):
        """Regex pattern must be compilable."""
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            CommentPattern(
                syntax="hash",
                prefix="[invalid(regex",  # Unclosed bracket
                filepath_line_regex="^#.*$",
                metadata_line_regex="^#.*$",
            )


class TestMetadataField:
    """Test metadata field model validation."""

    def test_valid_template_field(self):
        """RED: Template field should validate."""
        field = MetadataField(name="template", format_regex=r"^[a-z0-9_-]+$", required=True)
        assert field.name == "template"
        assert field.required is True

    def test_valid_timestamp_field(self):
        """RED: Timestamp field with ISO format should validate."""
        field = MetadataField(
            name="created", format_regex=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", required=True
        )
        assert field.name == "created"

    def test_optional_path_field(self):
        """RED: Optional path field should validate."""
        field = MetadataField(name="path", format_regex=r"^[a-zA-Z0-9_/.-]+$", required=False)
        assert field.required is False

    def test_invalid_name_fails(self):
        """RED: Empty field name should fail."""
        with pytest.raises(ValidationError):
            MetadataField(name="", format_regex=".*", required=True)

    def test_invalid_regex_fails(self):
        """RED: Empty regex should fail validation."""
        with pytest.raises(ValidationError):
            MetadataField(name="template", format_regex="", required=True)

    def test_invalid_regex_pattern_fails(self):
        """Field regex must be compilable."""
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            MetadataField(
                name="template",
                format_regex="(?P<incomplete",  # Incomplete named group
                required=True,
            )


class TestScaffoldMetadataConfig:
    """Test main configuration model."""

    def test_load_from_valid_yaml(self, tmp_path):
        """RED: Should load valid YAML config (2-line format)."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
version: "2.0"

comment_patterns:
  - syntax: hash
    prefix: "#\\\\s*"
    filepath_line_regex: "^#\\\\s*(.+\\\\.py)$"
    metadata_line_regex: "^#\\\\s*template=.+\\\\s+version=.+\\\\s+created=.+\\\\s+updated=.*$"

  - syntax: double_slash
    prefix: "//\\\\s*"
    filepath_line_regex: "^//\\\\s*(.+\\\\.ts)$"
    metadata_line_regex: "^//\\\\s*template=.+\\\\s+version=.+\\\\s+created=.+\\\\s+updated=.*$"

metadata_fields:
  - name: template
    format_regex: "^[a-z0-9_-]+$"
    required: true

  - name: version
    format_regex: "^[0-9a-f]{8}$|^$"
    required: true

  - name: created
    format_regex: "^\\\\d{4}-\\\\d{2}-\\\\d{2}T\\\\d{2}:\\\\d{2}(:\\\\d{2})?Z$"
    required: true

  - name: updated
    format_regex: "^(\\\\d{4}-\\\\d{2}-\\\\d{2}T\\\\d{2}:\\\\d{2}(:\\\\d{2})?Z)?$"
    required: false
""",
            encoding="utf-8",
        )

        config = ScaffoldMetadataConfig.from_file(config_file)

        assert len(config.comment_patterns) == 2
        assert len(config.metadata_fields) == 4  # No path field anymore
        assert config.comment_patterns[0].syntax == "hash"
        assert config.metadata_fields[0].name == "template"

    def test_get_pattern_by_syntax(self, tmp_path):
        """RED: Should retrieve pattern by syntax (2-line format)."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
comment_patterns:
  - syntax: hash
    prefix: "#\\\\s*"
    filepath_line_regex: "^#\\\\s*(.+\\\\.py)$"
    metadata_line_regex: "^#\\\\s*template=.+\\\\s+version=.+\\\\s+created=.+\\\\s+updated=.*$"

metadata_fields:
  - name: template
    format_regex: "^[a-z0-9_-]+$"
    required: true
""",
            encoding="utf-8",
        )

        config = ScaffoldMetadataConfig.from_file(config_file)
        pattern = config.get_pattern("hash")

        assert pattern is not None
        assert pattern.syntax == "hash"

    def test_get_pattern_not_found_returns_none(self, tmp_path):
        """RED: Should return None for unknown syntax (2-line format)."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
comment_patterns:
  - syntax: hash
    prefix: "#\\\\s*"
    filepath_line_regex: "^#\\\\s*(.+\\\\.py)$"
    metadata_line_regex: "^#\\\\s*template=.+\\\\s+version=.+\\\\s+created=.+\\\\s+updated=.*$"

metadata_fields:
  - name: template
    format_regex: "^[a-z0-9_-]+$"
    required: true
""",
            encoding="utf-8",
        )

        config = ScaffoldMetadataConfig.from_file(config_file)
        pattern = config.get_pattern("nonexistent")

        assert pattern is None

    def test_get_field_by_name(self, tmp_path):
        """RED: Should retrieve field by name (2-line format)."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
comment_patterns:
  - syntax: hash
    prefix: "#\\\\s*"
    filepath_line_regex: "^#\\\\s*(.+\\\\.py)$"
    metadata_line_regex: "^#\\\\s*template=.+\\\\s+version=.+\\\\s+created=.+\\\\s+updated=.*$"

metadata_fields:
  - name: template
    format_regex: "^[a-z0-9_-]+$"
    required: true

  - name: version
    format_regex: "^[0-9a-f]{8}$|^$"
    required: true
""",
            encoding="utf-8",
        )

        config = ScaffoldMetadataConfig.from_file(config_file)
        field = config.get_field("version")

        assert field is not None
        assert field.name == "version"
        assert field.required is True

    def test_get_field_not_found_returns_none(self, tmp_path):
        """RED: Should return None for unknown field (2-line format)."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
comment_patterns:
  - syntax: hash
    prefix: "#\\\\s*"
    filepath_line_regex: "^#\\\\s*(.+\\\\.py)$"
    metadata_line_regex: "^#\\\\s*template=.+\\\\s+version=.+\\\\s+created=.+\\\\s+updated=.*$"

metadata_fields:
  - name: template
    format_regex: "^[a-z0-9_-]+$"
    required: true
""",
            encoding="utf-8",
        )

        config = ScaffoldMetadataConfig.from_file(config_file)
        field = config.get_field("nonexistent")

        assert field is None

    def test_invalid_yaml_fails(self, tmp_path):
        """RED: Invalid YAML should raise ConfigError with hint."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text("invalid: [yaml", encoding="utf-8")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            ScaffoldMetadataConfig.from_file(config_file)

    def test_missing_file_raises_config_error(self, tmp_path):
        """Missing config file should raise ConfigError with hint."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError, match="Config file not found"):
            ScaffoldMetadataConfig.from_file(nonexistent)

    def test_missing_required_fields_fails(self, tmp_path):
        """RED: Missing required config keys should fail with ConfigError."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
comment_patterns:
  - syntax: hash
    prefix: "#\\\\s*"
    metadata_line_regex: "^#\\\\s*SCAFFOLD:\\\\s*(.+)$"
# metadata_fields missing!
""",
            encoding="utf-8",
        )

        with pytest.raises(ConfigError, match="Config validation failed"):
            ScaffoldMetadataConfig.from_file(config_file)

    def test_empty_patterns_list_fails(self, tmp_path):
        """RED: Empty comment patterns should fail with ConfigError."""
        config_file = tmp_path / "scaffold_metadata.yaml"
        config_file.write_text(
            """
comment_patterns: []

metadata_fields:
  - name: template
    format_regex: "^[a-z0-9_-]+$"
    required: true
""",
            encoding="utf-8",
        )

        with pytest.raises(ConfigError, match="Config validation failed"):
            ScaffoldMetadataConfig.from_file(config_file)
