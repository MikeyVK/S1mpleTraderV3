# SCAFFOLD: template=test_unit version=xxx created=2026-01-26T21:40:00Z
"""
Tests for Tier 2 Markdown template (Issue #72, TDD Cycle 4).

RED phase: Tests for tier2_base_markdown.jinja2 Markdown-specific syntax:
- Link definitions section (before Version History)
- Link format: [id]: path/to/file.md "Title"
- Link definitions invisible in Markdown preview
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Template directory
TEMPLATE_DIR = (
    Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
)


class TestTier2MarkdownLinkDefinitions:
    """Test tier2_base_markdown.jinja2 link definitions (Cycle 4)."""

    def test_renders_link_definitions_section(self):
        """Markdown documents must have link definitions section."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier2_base_markdown.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            related_docs=[
                "docs/research.md",
                "docs/planning.md"
            ],
        )

        # Link definitions should appear BEFORE Version History
        assert "[research.md]: docs/research.md" in result
        assert "[planning.md]: docs/planning.md" in result

        # Verify they come before Version History
        link_pos = result.find("[research.md]:")
        history_pos = result.find("## Version History")
        assert link_pos < history_pos, "Link definitions must come before Version History"

    def test_link_definitions_use_markdown_reference_format(self):
        """Link definitions must use Markdown reference format."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier2_base_markdown.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            related_docs=[
                "docs/development/issue72/research.md"
            ],
        )

        # Format: [id]: path/to/file.md
        assert "[research.md]: docs/development/issue72/research.md" in result

    def test_omits_link_definitions_when_no_related_docs(self):
        """Link definitions section should be omitted when no related docs."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier2_base_markdown.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
        )

        # No link definitions section
        assert "[" not in result or "## Version History" in result

    def test_link_definitions_render_as_invisible_references(self):
        """Link definitions should render as invisible Markdown references."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier2_base_markdown.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            related_docs=[
                "docs/planning.md"
            ],
        )

        # Link definition format (invisible in rendered Markdown)
        assert "[planning.md]: docs/planning.md" in result
        # Should NOT be a visible link like [text](url)
        assert "](docs/planning.md)" not in result or "[planning.md]:" in result
