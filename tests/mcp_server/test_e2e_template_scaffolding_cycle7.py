"""End-to-End test for complete template scaffolding (TDD Cycle 7).

Tests full template chain: tier0 → tier1 → tier2 → concrete design.
Validates SCAFFOLD metadata, link definitions, Version History, and GUIDELINE enforcement.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from mcp_server.validation.template_analyzer import TemplateAnalyzer


def _render_full_design_doc() -> str:
    """Helper: Render complete design document with realistic context."""
    template_dir = Path("mcp_server/scaffolding/templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("concrete/design.md.jinja2")

    return template.render(
        # tier0 variables (SCAFFOLD metadata)
        artifact_type="design",
        version_hash="abc123def456",
        timestamp="2026-01-26T15:30:00Z",
        output_path="docs/development/issue72/template-hierarchy-design.md",
        format="markdown",
        # tier1 variables (universal document structure)
        title="Template Hierarchy Design",
        status="Draft",
        phase="Design",
        purpose="Define 5-tier template hierarchy for artifact generation",
        scope_in="Template structure, inheritance chain, metadata enforcement",
        scope_out="Specific concrete templates, runtime scaffolding logic",
        prerequisites=["Issue #52 validation framework", "Jinja2 knowledge"],
        related_docs=[
            "docs/development/issue72/research.md",
            "docs/development/issue72/planning.md",
        ],
        # tier2 variables (Markdown-specific)
        frontmatter={
            "title": "Template Hierarchy Design",
            "type": "design",
            "created": "2026-01-26",
        },
        # concrete/design variables (DESIGN_TEMPLATE structure)
        problem_statement="Need structured, maintainable template system",
        requirements="5-tier hierarchy, metadata enforcement, inheritance",
        constraints="Must work with existing Jinja2, backward compatible SCAFFOLD",
        options=[
            {
                "name": "Flat Templates",
                "description": "Single template per artifact type",
                "pros": ["Simple", "Easy to understand"],
                "cons": ["Duplication", "Hard to maintain"],
            },
            {
                "name": "5-Tier Hierarchy",
                "description": "Layered templates with inheritance",
                "pros": ["DRY", "Maintainable", "Extensible"],
                "cons": ["More complexity", "Learning curve"],
            },
        ],
        decision="Use 5-tier hierarchy (tier0→tier1→tier2→tier3→concrete)",
        rationale="Best balance of maintainability and flexibility",
        key_decisions=[
            {
                "decision": "Use Jinja2 extends",
                "rationale": "Native template inheritance",
                "tradeoffs": "Tight coupling to Jinja2",
            },
            {
                "decision": "STRICT enforcement for BASE",
                "rationale": "Structural integrity",
                "tradeoffs": "Less flexibility",
            },
        ],
        open_questions=[
            "How to handle template versioning?",
            "Migration path for existing files?",
        ],
    )


class TestScaffoldDesignDocumentE2E:
    """Test complete design document scaffolding end-to-end (Cycle 7)."""

    def test_e2e_tier0_scaffold_metadata(self):
        """Validate tier0 SCAFFOLD metadata in 2-line format."""
        result = _render_full_design_doc()

        # 2-line format: Line 1 = filepath, Line 2 = metadata
        expected_path = "<!-- docs/development/issue72/template-hierarchy-design.md -->"
        assert expected_path in result

        expected_meta = (
            "<!-- template=design version=abc123def456 created=2026-01-26T15:30:00Z updated= -->"
        )
        assert expected_meta in result

        # NO "SCAFFOLD:" prefix
        assert "SCAFFOLD:" not in result

    def test_e2e_tier1_universal_document_structure(self):
        """Validate tier1 universal document structure elements."""
        result = _render_full_design_doc()

        # Title and multi-line header fields (no frontmatter)
        assert "# Template Hierarchy Design" in result
        assert "**Status:** Draft" in result
        assert "**Version:** 1.0" in result
        assert "**Last Updated:** 2026-01-26" in result

        # Purpose section
        assert "## Purpose" in result
        assert "Define 5-tier template hierarchy for artifact generation" in result

        # Scope section
        assert "## Scope" in result
        assert "**In Scope:**" in result
        assert "Template structure, inheritance chain, metadata enforcement" in result
        assert "**Out of Scope:**" in result
        assert "Specific concrete templates, runtime scaffolding logic" in result

        # Prerequisites
        assert "## Prerequisites" in result
        assert "Issue #52 validation framework" in result
        assert "Jinja2 knowledge" in result

        # Related Documentation and Version History
        assert "## Related Documentation" in result
        assert "## Version History" in result
        assert "| Version | Date | Author | Changes |" in result

    def test_e2e_tier2_markdown_patterns(self):
        """Validate tier2 Markdown-specific patterns (NO frontmatter, link definitions)."""
        result = _render_full_design_doc()

        # NO frontmatter (removed per BASE_TEMPLATE alignment)
        lines = result.split("\n")
        non_comment_lines = [
            line for line in lines if line.strip() and not line.strip().startswith("<!--")
        ]
        # First non-comment line should be title
        assert non_comment_lines[0].startswith("# ")

        # Link definitions (still present)
        assert "[related-1]: docs/development/issue72/research.md" in result
        assert "[related-2]: docs/development/issue72/planning.md" in result

        # Verify link definitions come BEFORE Version History
        link_pos = result.find("[related-1]:")
        history_pos = result.find("## Version History")
        assert link_pos < history_pos, "Link definitions must come before Version History"

    def test_e2e_concrete_design_template_structure(self):
        """Validate concrete DESIGN_TEMPLATE numbered sections."""
        result = _render_full_design_doc()

        # Section 1: Context & Requirements with numbered subsections
        assert "## 1. Context & Requirements" in result
        assert "### 1.1. Problem Statement" in result
        assert "Need structured, maintainable template system" in result
        assert "### 1.2. Requirements" in result
        assert "**Functional:**" in result  # Requirements subsections
        assert "### 1.3. Constraints" in result
        assert "Must work with existing Jinja2" in result

        # Section 2: Design Options with numbered subsections
        assert "## 2. Design Options" in result
        assert "### 2.1. Option A: Flat Templates" in result
        assert "Single template per artifact type" in result
        assert "**Pros:**" in result
        assert "- ✅ Simple" in result  # Checkmark format
        assert "**Cons:**" in result
        assert "- ❌ Duplication" in result  # X format
        assert "### 2.2. Option B: 5-Tier Hierarchy" in result
        assert "Layered templates with inheritance" in result

    def test_e2e_concrete_design_chosen_design_section(self):
        """Validate concrete DESIGN_TEMPLATE Chosen Design section."""
        result = _render_full_design_doc()

        # Section 3: Chosen Design (not subsections, but **Decision:** format)
        assert "## 3. Chosen Design" in result
        assert "**Decision:** Use 5-tier hierarchy (tier0→tier1→tier2→tier3→concrete)" in result
        assert "**Rationale:** Best balance of maintainability and flexibility" in result

        # Key Decisions table (2 columns now)
        assert "### 3.1. Key Design Decisions" in result
        assert "| Decision | Rationale |" in result
        assert "Use Jinja2 extends" in result

        # Section 4: Open Questions (table format)
        assert "## 4. Open Questions" in result
        assert "| Question | Options | Status |" in result
        assert "How to handle template versioning?" in result
        assert "Migration path for existing files?" in result

    def test_e2e_with_missing_optional_fields(self):
        """E2E test with minimal required fields (edge case)."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            # Required fields only
            artifact_type="design",
            version_hash="test123",
            timestamp="2026-01-26T10:00:00Z",
            output_path="docs/test.md",
            format="markdown",
            title="Minimal Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            problem_statement="Problem",
            requirements="Requirements",
            decision="Decision",
            rationale="Rationale",
            options=[],
            key_decisions=[],
        )

        # Should still have all required sections
        assert "# Minimal Design" in result
        assert "## Purpose" in result
        assert "## 1. Context & Requirements" in result
        assert "## 2. Design Options" in result
        assert "## 3. Chosen Design" in result

        # Optional sections should be omitted or show defaults
        assert "## Prerequisites" not in result
        assert "## 4. Open Questions" not in result
        assert "None" in result  # related_docs defaults to "None"

    def test_e2e_guideline_enforcement(self):
        """Validate that design template uses GUIDELINE enforcement (not STRICT)."""
        template_root = Path("mcp_server/scaffolding/templates")
        analyzer = TemplateAnalyzer(template_root)

        design_path = template_root / "concrete" / "design.md.jinja2"
        metadata = analyzer.extract_metadata(design_path)

        # GUIDELINE enforcement means violations are warnings, not errors
        assert metadata["enforcement"] == "GUIDELINE"
        assert "guidelines" in metadata["validates"]

        strict_rules = metadata["validates"].get("strict", [])
        assert "strict" not in metadata["validates"] or not strict_rules
