"""
Unit tests for Label dataclass.

Tests immutable label definition with color validation.

@layer: Tests (Unit)
@dependencies: [pytest, dataclasses, mcp_server.config.label_config]
"""

# Standard library
from dataclasses import FrozenInstanceError

# Third-party
import pytest

# Project modules
from mcp_server.config.label_config import Label


class TestLabelCreation:
    """Test Label dataclass creation with various inputs."""

    def test_label_creation_valid(self):
        """Create label with valid color."""
        label = Label(name="type:feature", color="1D76DB")
        assert label.name == "type:feature"
        assert label.color == "1D76DB"
        assert label.description == ""

    def test_label_creation_with_description(self):
        """Create label with optional description."""
        label = Label(
            name="type:bug",
            color="D73A4A",
            description="Something isn't working"
        )
        assert label.name == "type:bug"
        assert label.color == "D73A4A"
        assert label.description == "Something isn't working"

    def test_label_creation_lowercase_color(self):
        """Accept lowercase hex color."""
        label = Label(name="priority:high", color="ff0000")
        assert label.color == "ff0000"

    def test_label_creation_uppercase_color(self):
        """Accept uppercase hex color."""
        label = Label(name="priority:low", color="FF0000")
        assert label.color == "FF0000"

    def test_label_creation_mixed_color(self):
        """Accept mixed case hex color."""
        label = Label(name="phase:design", color="AbC123")
        assert label.color == "AbC123"


class TestLabelColorValidation:
    """Test Label color format validation."""

    def test_label_invalid_color_hash_prefix(self):
        """Reject color with # prefix."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="#ff0000")

    def test_label_invalid_color_too_short(self):
        """Reject color that is too short."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="ff00")

    def test_label_invalid_color_non_hex(self):
        """Reject color with non-hex characters."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="gggggg")


class TestLabelImmutability:
    """Test Label immutability (frozen=True)."""

    def test_label_immutable(self):
        """Verify frozen=True prevents modification."""
        label = Label(name="type:feature", color="1D76DB")
        with pytest.raises(FrozenInstanceError):
            label.name = "type:bug"


class TestLabelConversion:
    """Test Label conversion methods."""

    def test_label_to_github_dict(self):
        """Convert Label to GitHub API format."""
        label = Label(
            name="type:feature",
            color="1D76DB",
            description="New feature"
        )
        result = label.to_github_dict()

        assert result == {
            "name": "type:feature",
            "color": "1D76DB",
            "description": "New feature"
        }

    def test_label_to_github_dict_no_description(self):
        """Convert Label without description to GitHub format."""
        label = Label(name="priority:high", color="D93F0B")
        result = label.to_github_dict()

        assert result == {
            "name": "priority:high",
            "color": "D93F0B",
            "description": ""
        }
