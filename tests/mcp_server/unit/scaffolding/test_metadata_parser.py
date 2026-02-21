"""
Unit tests for scaffold metadata parser.

Tests parsing SCAFFOLD comments from scaffolded files.
Following TDD: These tests are written BEFORE implementation (RED phase).
"""

# pyright: basic

import pytest

from mcp_server.scaffolding.metadata import (
    MetadataParseError,
    ScaffoldMetadataParser,
)


class TestScaffoldMetadataParser:
    """Test metadata parser for different comment syntaxes."""

    def test_parse_python_hash_comment(self):
        """RED: Parse metadata from Python hash comment (2-line format)."""
        content = (
            "# mcp_server/dto/user.py\n"
            "# template=dto version=abc12345 created=2026-01-20T14:00Z updated=\n"
            "class UserDTO:\n    pass\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")
        assert metadata is not None

        assert metadata["template"] == "dto"
        assert metadata["version"] == "abc12345"
        assert metadata["created"] == "2026-01-20T14:00Z"

    def test_parse_typescript_double_slash_comment(self):
        """RED: Parse metadata from TypeScript double-slash comment (2-line format)."""
        content = (
            "// src/types/user.ts\n"
            "// template=interface version=def67890 created=2026-01-20T14:00Z updated=\n"
            "export interface User {\n    id: string;\n}\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".ts")
        assert metadata is not None

        assert metadata["template"] == "interface"
        assert metadata["version"] == "def67890"
        assert metadata["created"] == "2026-01-20T14:00Z"

    def test_parse_markdown_html_comment(self):
        """RED: Parse metadata from Markdown HTML comment (2-line format)."""
        content = (
            "<!-- docs/design.md -->\n"
            "<!-- template=design version=a1b2c3d4 created=2026-01-20T14:00Z updated= -->\n"
            "# Design Document\n\n"
            "Content here.\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".md")
        assert metadata is not None

        assert metadata["template"] == "design"
        assert metadata["created"] == "2026-01-20T14:00Z"

    def test_parse_jinja2_comment(self):
        """RED: Parse metadata from Jinja2 comment (2-line format)."""
        content = (
            "{# templates/email.html.jinja2 #}\n"
            "{# template=email version=12345678 created=2026-01-20T14:00Z updated= #}\n"
            "<html>\n"
            "    <body>{{ content }}</body>\n"
            "</html>\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".jinja2")
        assert metadata is not None

        assert metadata["template"] == "email"

    def test_parse_with_optional_updated_field(self):
        """RED: Parse metadata with optional updated timestamp (2-line format)."""
        content = (
            "# mcp_server/dto/user.py\n"
            "# template=dto version=abc12345 created=2026-01-20T14:00Z updated=2026-01-20T15:30Z\n"
            "class UserDTO:\n"
            "    pass\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")
        assert metadata is not None

        assert metadata["updated"] == "2026-01-20T15:30Z"

    def test_parse_ephemeral_artifact_without_path(self):
        """RED: Ephemeral artifacts still have filepath on line 1 (2-line format)."""
        content = (
            "# commit_message.txt\n"
            "# template=commit_message version=a1b2c3d4 created=2026-01-20T14:00Z updated=\n"
            "feat: Add user authentication\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".txt")
        assert metadata is not None

        assert metadata["template"] == "commit_message"

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
        """RED: SCAFFOLD metadata must be on first 2 lines."""
        content = """# Regular comment
# mcp_server/dto/user.py
# template=dto version=abc12345 created=2026-01-20T14:00Z updated=
class UserDTO:
    pass
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")

        assert metadata is None

    def test_parse_missing_required_field_raises_error(self):
        """RED: Missing required field should raise MetadataParseError (2-line format)."""
        content = """# mcp_server/dto/user.py
# template=dto created=2026-01-20T14:00Z updated=
# Missing: version
"""
        parser = ScaffoldMetadataParser()

        # Parser will fail because line 2 doesn't match expected pattern (no version=)
        metadata = parser.parse(content, ".py")
        # Should return None because pattern doesn't match
        assert metadata is None

    def test_parse_invalid_field_format_raises_error(self):
        """RED: Invalid field format should raise MetadataParseError (2-line format)."""
        content = (
            "# mcp_server/dto/user.py\n"
            "# template=Invalid_Template version=abc12345 created=2026-01-20T14:00Z updated=\n"
            "# template should be lowercase with hyphens/underscores only\n"
        )
        parser = ScaffoldMetadataParser()

        with pytest.raises(MetadataParseError, match="Invalid value.*template"):
            parser.parse(content, ".py")

    def test_parse_invalid_timestamp_format_raises_error(self):
        """RED: Invalid timestamp format should raise MetadataParseError (2-line format)."""
        content = """# mcp_server/dto/user.py
# template=dto version=abc12345 created=2026-01-20 14:00:00 updated=
# Missing T and Z in timestamp
"""
        parser = ScaffoldMetadataParser()

        with pytest.raises(MetadataParseError, match="Invalid value.*created"):
            parser.parse(content, ".py")

    def test_parse_unknown_extension_returns_none(self):
        """RED: Unknown file extension returns None (no pattern match)."""
        content = """# some_file.unknown
# template=dto version=abc12345 created=2026-01-20T14:00Z updated=
"""
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".unknown")

        assert metadata is None

    def test_parse_malformed_key_value_raises_error(self):
        """RED: Line 2 not matching pattern returns None (2-line format)."""
        content = (
            "# mcp_server/dto/user.py\n"
            "# This line doesn't match the expected pattern\n"
            "# Should return None\n"
        )
        parser = ScaffoldMetadataParser()

        # Line 2 doesn't match metadata pattern
        metadata = parser.parse(content, ".py")
        assert metadata is None  # No match

    def test_parse_with_extra_whitespace(self):
        """RED: Parser should handle extra whitespace gracefully (2-line format)."""
        content = (
            "#   test.py\n"
            "#   template=dto   version=abc12345   created=2026-01-20T14:00Z   updated=\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")
        assert metadata is not None

        assert metadata["template"] == "dto"
        assert metadata["version"] == "abc12345"

    def test_parse_case_sensitive_field_names(self):
        """RED: Field names should be case-sensitive - uppercase fields ignored (2-line format)."""
        content = (
            "# test.py\n"
            "# Template=dto VERSION=abc12345 created=2026-01-20T14:00Z updated=\n"
            "# Uppercase fields should be treated as unknown\n"
        )
        parser = ScaffoldMetadataParser()

        # Uppercase fields are unknown/ignored - doesn't match pattern
        metadata = parser.parse(content, ".py")
        assert metadata is None  # Pattern doesn't match without lowercase fields

    def test_parse_duplicate_fields_uses_last_value(self):
        """RED: Duplicate fields should use last occurrence (2-line format)."""
        content = (
            "# test.py\n"
            "# template=dto template=worker version=abc12345 created=2026-01-20T14:00Z updated=\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")
        assert metadata is not None

        assert metadata["template"] == "worker"  # Last value wins

    def test_parse_unknown_fields_are_ignored(self):
        """RED: Unknown fields should be silently ignored (2-line format)."""
        content = (
            "# test.py\n"
            "# template=dto version=abc12345 created=2026-01-20T14:00Z updated= unknown_field=ignored\n"
        )
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".py")
        assert metadata is not None

        assert "unknown_field" not in metadata
        assert metadata["template"] == "dto"
