# tests\test_tier0_conditional_header.py
# template=unit_test version=3d15d309 created=2026-02-21T15:27Z updated=
"""
Unit tests for tier0_base_artifact.jinja2.

Tests for tier0_base_artifact.jinja2 conditional SCAFFOLD header (Issue #239 C1).

RED phase: output_path=None / '' → compact single-line HTML-comment.
           output_path=str → existing two-line format unchanged (regression).

@layer: Tests (Unit)
@dependencies: [pytest, jinja2]
@responsibilities:
    - Test TestTier0ConditionalHeader functionality
    - Verify conditional header rendering based on output_path value
    - Cover regression: existing two-line format for file artifacts unchanged
"""

# Standard library
from pathlib import Path

# Third-party
import pytest
from jinja2 import Environment, FileSystemLoader, Template

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "mcp_server" / "scaffolding" / "templates"


@pytest.fixture
def tier0() -> Template:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    return env.get_template("tier0_base_artifact.jinja2")


class TestTier0ConditionalHeader:
    """Test suite for tier0_base_artifact.jinja2 conditional SCAFFOLD header."""

    def test_none_output_path_renders_compact_header(self, tier0: Template) -> None:
        """output_path=None must produce exactly one compact metadata comment."""
        # Arrange
        # Act
        result = tier0.render(
            artifact_type="issue",
            version_hash="8b7bb3ab",
            timestamp="2026-02-21T15:00Z",
            output_path=None,
            format="markdown",
        )

        # Assert
        lines = [line for line in result.strip().split("\n") if line.strip()]
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"
        assert lines[0] == "<!-- template=issue version=8b7bb3ab -->", (
            f"Unexpected compact header: {lines[0]}"
        )

    def test_empty_output_path_renders_compact_header(self, tier0: Template) -> None:
        """output_path='' (empty string) treated as None — compact header."""
        # Arrange
        # Act
        result = tier0.render(
            artifact_type="issue",
            version_hash="8b7bb3ab",
            timestamp="2026-02-21T15:00Z",
            output_path="",
            format="markdown",
        )

        # Assert
        lines = [line for line in result.strip().split("\n") if line.strip()]
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"
        assert lines[0] == "<!-- template=issue version=8b7bb3ab -->", (
            f"Unexpected compact header: {lines[0]}"
        )

    def test_compact_header_has_no_created_or_updated(self, tier0: Template) -> None:
        """Compact header must NOT contain created= or updated= fields."""
        # Arrange
        # Act
        result = tier0.render(
            artifact_type="issue",
            version_hash="8b7bb3ab",
            timestamp="2026-02-21T15:00Z",
            output_path=None,
            format="markdown",
        )

        # Assert
        assert "created=" not in result, "Compact header must not contain created="
        assert "updated=" not in result, "Compact header must not contain updated="

    def test_compact_header_has_no_empty_filepath_comment(self, tier0: Template) -> None:
        """Compact header must NOT render a blank filepath comment like <!--  -->."""
        # Arrange
        # Act
        result = tier0.render(
            artifact_type="issue",
            version_hash="8b7bb3ab",
            timestamp="2026-02-21T15:00Z",
            output_path=None,
            format="markdown",
        )

        # Assert
        assert "<!--  -->" not in result, "Must not render empty filepath comment"

    def test_non_empty_output_path_renders_two_line_markdown(self, tier0: Template) -> None:
        """Non-empty output_path must produce the existing two-line markdown format (regression)."""
        # Arrange
        # Act
        result = tier0.render(
            artifact_type="research",
            version_hash="b4e8f3c2",
            timestamp="2026-01-23T09:15:00Z",
            output_path="docs/development/issue72/research.md",
            format="markdown",
        )

        # Assert
        lines = result.strip().split("\n")
        assert lines[0] == "<!-- docs/development/issue72/research.md -->", (
            f"Line 1 must be filepath, got: {lines[0]}"
        )
        assert lines[1].startswith("<!-- template=research version=b4e8f3c2"), (
            f"Line 2 must be metadata, got: {lines[1]}"
        )
        assert "created=2026-01-23T09:15:00Z" in lines[1]
        assert "updated=" in lines[1]

    def test_non_empty_output_path_renders_two_line_python(self, tier0: Template) -> None:
        """Non-empty output_path must produce the existing two-line python format (regression)."""
        # Arrange
        # Act
        result = tier0.render(
            artifact_type="worker",
            version_hash="a3f7b2c1",
            timestamp="2026-01-23T10:30:00Z",
            output_path="src/workers/MyWorker.py",
            format="python",
        )

        # Assert
        lines = result.strip().split("\n")
        assert lines[0] == "# src/workers/MyWorker.py", f"Line 1 must be filepath, got: {lines[0]}"
        assert "template=worker" in lines[1]
        assert "version=a3f7b2c1" in lines[1]
        assert "created=2026-01-23T10:30:00Z" in lines[1]
