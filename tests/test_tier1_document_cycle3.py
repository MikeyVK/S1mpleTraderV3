# SCAFFOLD: template=test_unit version=xxx created=2026-01-26T21:30:00Z
"""
Tests for Tier 1 document template (Issue #72, TDD Cycle 3).

RED phase: Tests for tier1_base_document.jinja2 universal document structure:
- Status/Phase fields
- Purpose section
- Scope (In/Out)
- Prerequisites (optional)
- Related Documentation
- Version History table
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Template directory
TEMPLATE_DIR = (
    Path(__file__).parent.parent / "mcp_server" / "scaffolding" / "templates"
)


class TestTier1DocumentUniversalStructure:
    """Test tier1_base_document.jinja2 universal structure (Cycle 3)."""

    def test_renders_status_and_phase_fields(self):
        """Document must have Status, Version, Last Updated fields (Phase removed per BASE_TEMPLATE)."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            status="Draft",
            version="1.0",
            last_updated="2026-01-26",
            purpose="Test purpose",
            scope_in="Feature X",
            scope_out="Feature Y",
        )

        assert "**Status:** Draft" in result, "Status field missing"
        assert "**Version:** 1.0" in result, "Version field missing"
        assert "**Last Updated:** 2026-01-26" in result, "Last Updated field missing"

    def test_renders_purpose_section(self):
        """Document must have Purpose section."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            purpose="Define the architecture for feature X",
            scope_in="Feature X",
            scope_out="Feature Y",
        )

        assert "## Purpose" in result, "Purpose section missing"
        assert "Define the architecture for feature X" in result

    def test_renders_scope_in_and_out(self):
        """Document must have Scope with In Scope and Out of Scope."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

        result = template.render(
            artifact_type="design",
            version_hash="abc123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/design.md",
            format="markdown",
            title="Test Design",
            purpose="Test",
            scope_in="API endpoints, Database schema",
            scope_out="Frontend implementation, Testing",
        )

        assert "## Scope" in result, "Scope section missing"
        assert "**In Scope:**" in result, "In Scope label missing"
        assert "API endpoints, Database schema" in result
        assert "**Out of Scope:**" in result, "Out of Scope label missing"
        assert "Frontend implementation, Testing" in result

    def test_renders_prerequisites_when_provided(self):
        """Prerequisites section should render when provided."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

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
            prerequisites=["Research complete", "Stakeholder approval"],
        )

        assert "## Prerequisites" in result, "Prerequisites section missing"
        assert "Research complete" in result
        assert "Stakeholder approval" in result

    def test_omits_prerequisites_when_not_provided(self):
        """Prerequisites section should be omitted when not provided."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

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

        assert "## Prerequisites" not in result

    def test_renders_related_documentation(self):
        """Document must have Related Documentation section with reference-style links."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

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
            related_docs=["planning.md", "research.md"],
        )

        assert "## Related Documentation" in result
        # Template uses reference-style links with auto-generated IDs
        assert "related-" in result  # Should have reference IDs

    def test_renders_version_history_table(self):
        """Document must have Version History table (column order: Version, Date, Author, Changes)."""
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("tier1_base_document.jinja2")

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

        assert "## Version History" in result
        # Updated column order per BASE_TEMPLATE: Version | Date | Author | Changes
        assert "| Version | Date | Author | Changes |" in result
        assert "| 1.0 |" in result  # Default version
        assert "| Agent |" in result  # Default author
        assert "| Initial draft |" in result  # Default changes
