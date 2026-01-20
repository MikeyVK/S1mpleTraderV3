"""
Unit tests for scaffold metadata parser.

Tests parsing SCAFFOLD comments from scaffolded files.
Following TDD: These tests are written BEFORE implementation (RED phase).
"""

import pytest

from mcp_server.scaffolding.metadata import ScaffoldMetadataParser, MetadataParseError


class TestScaffoldMetadataParser:
    """Test metadata parser for different comment syntaxes."""

    def test_parse_python_hash_comment(self):
        """RED: Parse metadata from Python hash comment."""
        content = """# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z path=mcp_server/dto/user.py
class UserDTO:
    pass
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata["template"] == "dto"
        assert metadata["version"] == "1.0"
        assert metadata["created"] == "2026-01-20T14:00:00Z"
        assert metadata["path"] == "mcp_server/dto/user.py"

    def test_parse_typescript_double_slash_comment(self):
        """RED: Parse metadata from TypeScript double-slash comment."""
        content = """// SCAFFOLD: template=interface version=1.0 created=2026-01-20T14:00:00Z path=src/types/user.ts
export interface User {
    id: string;
}
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".ts")

        assert metadata["template"] == "interface"
        assert metadata["version"] == "1.0"
        assert metadata["created"] == "2026-01-20T14:00:00Z"

    def test_parse_markdown_html_comment(self):
        """RED: Parse metadata from Markdown HTML comment."""
        content = """<!-- SCAFFOLD: template=design version=1.0 created=2026-01-20T14:00:00Z path=docs/design.md -->
# Design Document

Content here.
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".md")

        assert metadata["template"] == "design"
        assert metadata["created"] == "2026-01-20T14:00:00Z"

    def test_parse_jinja2_comment(self):
        """RED: Parse metadata from Jinja2 comment."""
        content = """{# SCAFFOLD: template=email version=1.0 created=2026-01-20T14:00:00Z path=templates/email.html.jinja2 #}
<html>
    <body>{{ content }}</body>
</html>
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".jinja2")

        assert metadata["template"] == "email"
        assert metadata["path"] == "templates/email.html.jinja2"

    def test_parse_with_optional_updated_field(self):
        """RED: Parse metadata with optional updated timestamp."""
        content = """# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z updated=2026-01-20T15:30:00Z path=mcp_server/dto/user.py
class UserDTO:
    pass
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata["updated"] == "2026-01-20T15:30:00Z"

    def test_parse_ephemeral_artifact_without_path(self):
        """RED: Ephemeral artifacts without path field are valid."""
        content = """# SCAFFOLD: template=commit_message version=1.0 created=2026-01-20T14:00:00Z
feat: Add user authentication
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".txt")

        assert metadata["template"] == "commit_message"
        assert "path" not in metadata  # Ephemeral = no path

    def test_parse_non_scaffolded_file_returns_none(self):
        """RED: Non-scaffolded files should return None."""
        content = """# Just a regular Python file
class User:
    pass
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata is None

    def test_parse_empty_file_returns_none(self):
        """RED: Empty files should return None."""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse("", ".py")

        assert metadata is None

    def test_parse_scaffold_not_on_first_line_returns_none(self):
        """RED: SCAFFOLD comment must be on first line."""
        content = """# Regular comment
# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z
class UserDTO:
    pass
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata is None

    def test_parse_missing_required_field_raises_error(self):
        """RED: Missing required field should raise MetadataParseError."""
        content = """# SCAFFOLD: template=dto created=2026-01-20T14:00:00Z
# Missing: version
"""
        parser = ScaffoldMetadataParser()

        with pytest.raises(MetadataParseError, match="Missing required field: version"):
            parser.parse(content, ".py")

    def test_parse_invalid_field_format_raises_error(self):
        """RED: Invalid field format should raise MetadataParseError."""
        content = """# SCAFFOLD: template=Invalid_Template version=1.0 created=2026-01-20T14:00:00Z
# template should be lowercase with hyphens/underscores only
"""
        parser = ScaffoldMetadataParser()

        with pytest.raises(MetadataParseError, match="Invalid value.*template"):
            parser.parse(content, ".py")

    def test_parse_invalid_timestamp_format_raises_error(self):
        """RED: Invalid timestamp format should raise MetadataParseError."""
        content = """# SCAFFOLD: template=dto version=1.0 created=2026-01-20 14:00:00
# Missing T and Z in timestamp
"""
        parser = ScaffoldMetadataParser()

        with pytest.raises(MetadataParseError, match="Invalid value.*created"):
            parser.parse(content, ".py")

    def test_parse_unknown_extension_returns_none(self):
        """RED: Unknown file extension should return None (no pattern match)."""
        content = """# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".unknown")

        assert metadata is None

    def test_parse_malformed_key_value_raises_error(self):
        """RED: Malformed key=value pairs should raise MetadataParseError."""
        content = """# SCAFFOLD: template=dto version 1.0 created=2026-01-20T14:00:00Z
# 'version 1.0' is missing '=' - parsed as version=, missing version value
"""
        parser = ScaffoldMetadataParser()

        # Missing version value causes "Missing required field" error
        with pytest.raises(MetadataParseError, match="Missing required field: version"):
            parser.parse(content, ".py")

    def test_parse_with_extra_whitespace(self):
        """RED: Parser should handle extra whitespace gracefully."""
        content = """#   SCAFFOLD:   template=dto   version=1.0   created=2026-01-20T14:00:00Z   path=test.py
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata["template"] == "dto"
        assert metadata["version"] == "1.0"

    def test_parse_case_sensitive_field_names(self):
        """RED: Field names should be case-sensitive."""
        content = """# SCAFFOLD: Template=dto VERSION=1.0 created=2026-01-20T14:00:00Z
# Uppercase fields should be treated as unknown
"""
        parser = ScaffoldMetadataParser()

        # Should fail because 'template' and 'version' (lowercase) are required
        with pytest.raises(MetadataParseError, match="Missing required field"):
            parser.parse(content, ".py")

    def test_parse_duplicate_fields_uses_last_value(self):
        """RED: Duplicate fields should use last occurrence."""
        content = """# SCAFFOLD: template=dto template=worker version=1.0 created=2026-01-20T14:00:00Z
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata["template"] == "worker"  # Last value wins

    def test_parse_unknown_fields_are_ignored(self):
        """RED: Unknown fields should be silently ignored."""
        content = """# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z unknown_field=ignored
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert "unknown_field" not in metadata
        assert metadata["template"] == "dto"
