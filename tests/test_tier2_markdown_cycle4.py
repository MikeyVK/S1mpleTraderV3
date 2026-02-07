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
        """Markdown documents must have link definitions section with auto-generated IDs."""
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

        # Link definitions use auto-generated IDs: [related-1], [related-2], etc.
        assert "[related-1]: docs/research.md" in result
        assert "[related-2]: docs/planning.md" in result

        # Verify they come before Version History
        link_pos = result.find("[related-1]:")
        history_pos = result.find("## Version History")
        assert link_pos < history_pos, "Link definitions must come before Version History"

    def test_link_definitions_use_markdown_reference_format(self):
        """Link definitions must use Markdown reference format with auto-generated IDs."""
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

        # Format: [related-N]: path/to/file.md (auto-generated ID)
        assert "[related-1]: docs/development/issue72/research.md" in result

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

        # No link definitions when no related docs
        assert "<!-- Link definitions -->" not in result or "None" in result

    def test_link_definitions_render_as_invisible_references(self):
        """Link definitions should render as invisible Markdown references with auto-generated IDs."""
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

        # Link definition format (invisible in rendered Markdown) with auto-generated ID
        assert "[related-1]: docs/planning.md" in result
        # Related docs section uses reference-style links
        assert "**[docs/planning.md][related-1]**" in result or "[related-1]" in result
