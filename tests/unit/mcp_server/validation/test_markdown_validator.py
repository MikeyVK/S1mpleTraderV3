# tests/unit/mcp_server/validation/test_markdown_validator.py
"""
Unit tests for MarkdownValidator.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
import textwrap
from typing import Generator
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Module under test
from mcp_server.validation.markdown_validator import MarkdownValidator


class TestMarkdownValidator:
    """Test suite for MarkdownValidator."""

    @pytest.fixture
    def validator(self) -> Generator[MarkdownValidator, None, None]:
        """Fixture for MarkdownValidator."""
        yield MarkdownValidator()

    def test_init(self, validator: MarkdownValidator) -> None:
        """Test initialization and repr."""
        assert str(validator) == "MarkdownValidator()"

    @pytest.mark.asyncio
    async def test_validate_implicit_read_missing_file(
        self, validator: MarkdownValidator
    ) -> None:
        """Test validation failure when file does not exist (implicit read)."""
        with patch("pathlib.Path.exists", return_value=False):
            result = await validator.validate("im_ghost.md")
            assert result.passed is False
            assert result.issues[0].message == "File not found"

    @pytest.mark.asyncio
    async def test_validate_read_error(self, validator: MarkdownValidator) -> None:
        """Test validation failure on file read error."""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=OSError("Access denied")):
            result = await validator.validate("locked.md")
            assert result.passed is False
            assert "Failed to read file" in result.issues[0].message

    @pytest.mark.asyncio
    async def test_validate_missing_h1(self, validator: MarkdownValidator) -> None:
        """Test validation failure for missing H1 title."""
        content = textwrap.dedent("""
        ## Subtitle
        text
        """)
        result = await validator.validate("no_title.md", content)
        assert result.passed is False
        assert any("Missing H1 title" in i.message for i in result.issues)

    @pytest.mark.asyncio
    async def test_validate_valid_content(self, validator: MarkdownValidator) -> None:
        """Test validation of valid content."""
        content = textwrap.dedent("""
        # Valid Title
        text
        """)
        result = await validator.validate("valid.md", content)
        assert result.passed is True
        assert not result.issues

    @pytest.mark.asyncio
    async def test_validate_broken_links_simple(self, validator: MarkdownValidator) -> None:
        """Test broken links using a simpler mock strategy."""
        content = textwrap.dedent("""
        # Title
        [Bad](missing.png)
        """)

        # We need to catch: resolved_path.exists()
        # The logic is: Path(path).parent / target

        with patch("mcp_server.validation.markdown_validator.Path") as mock_path_cls:
            mock_file_path = MagicMock()
            mock_path_cls.return_value = mock_file_path

            mock_parent = MagicMock()
            mock_file_path.parent = mock_parent

            # (parent / target) -> returns a new path-like object
            mock_target_path_obj = MagicMock()
            mock_parent.__truediv__.return_value = mock_target_path_obj

            mock_resolved = MagicMock()
            mock_target_path_obj.resolve.return_value = mock_resolved

            # Crucial: exists() returns False to simulate broken link
            mock_resolved.exists.return_value = False

            result = await validator.validate("doc.md", content)

            assert result.passed is True  # Broken links are WARNINGS (severity='warning')
            assert result.score < 10.0    # check score penalty
            assert len(result.issues) == 1
            assert "Broken link" in result.issues[0].message
            assert result.issues[0].severity == "warning"

    @pytest.mark.asyncio
    async def test_validate_valid_links_ignore_external(self, validator: MarkdownValidator) -> None:
        """Test that external links and valid local links don't cause issues."""
        content = textwrap.dedent("""
        # Title
        [Ext](https://example.com)
        [Mail](mailto:user@example.com)
        [Anchor](#local)
        [File](exists.md)
        """)

        with patch("mcp_server.validation.markdown_validator.Path") as mock_path_cls:
            mock_file_path = MagicMock()
            mock_path_cls.return_value = mock_file_path
            mock_parent = MagicMock()
            mock_file_path.parent = mock_parent

            mock_target = MagicMock()
            mock_parent.__truediv__.return_value = mock_target
            mock_resolved = MagicMock()
            mock_target.resolve.return_value = mock_resolved

            # exists() returns True for the local file check
            mock_resolved.exists.return_value = True

            result = await validator.validate("doc.md", content)

            assert result.passed is True
            assert not result.issues
