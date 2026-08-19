"""End-to-End tests for complete design document scaffolding.

Tests full template chain: tier0 -> tier1 -> tier2 -> concrete design.
Validates SCAFFOLD metadata, link definitions, Version History, and section contracts.

@layer: Tests (Unit)
@dependencies: pytest, jinja2
"""

from jinja2 import Environment, FileSystemLoader

from tests.mcp_server.test_support import get_template_root


def _render_full_design_doc() -> str:
    """Helper: Render complete design document with current contract-shaped context."""
    template_dir = get_template_root()
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("concrete/design.md.jinja2")

    return template.render(
        # tier0 variables (SCAFFOLD metadata)
        artifact_type="design",
        version_hash="abc123def456",
        timestamp="2026-01-26T15:30:00Z",
        output_path="docs/development/issue72/template-hierarchy-design.md",
        format="markdown",
        # structural doc fields (now required in DocArtifactContext)
        status="DRAFT",
        version="1.0.0",
        last_updated="2026-01-26",
        # tier1 variables (universal document structure)
        title="Template Hierarchy Design",
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
        requirements_functional=[
            "Support 5-tier hierarchy",
            "Enforce metadata inheritance",
        ],
        requirements_nonfunctional=[
            "Remain maintainable as templates evolve",
        ],
        constraints=[
            "Must work with existing Jinja2",
            "Must preserve scaffold metadata output",
        ],
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
        decision="Use 5-tier hierarchy (tier0\u2192tier1\u2192tier2\u2192tier3\u2192concrete)",
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
    """End-to-end tests for design document scaffolding."""

    def test_e2e_tier0_scaffold_metadata(self) -> None:
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

    def test_e2e_tier2_markdown_patterns(self) -> None:
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

    def test_e2e_concrete_design_template_contract(self) -> None:
        """Validate stable concrete design contract, not fixture-specific internals."""
        result = _render_full_design_doc()

        # Section 1 contract: numbered headings plus supported requirement buckets
        assert "## 1. Context & Requirements" in result
        assert "### 1.1. Problem Statement" in result
        assert "Need structured, maintainable template system" in result
        assert "### 1.2. Requirements" in result
        assert "**Functional:**" in result
        assert "- [ ] Support 5-tier hierarchy" in result
        assert "**Non-Functional:**" in result
        assert "- [ ] Remain maintainable as templates evolve" in result
        assert "### 1.3. Constraints" in result
        assert "- Must work with existing Jinja2" in result

        # Section 2 contract: options render as numbered alternatives with pros/cons lists
        assert "## 2. Design Options" in result
        assert "### 2.1. Option A: Flat Templates" in result
        assert "### 2.2. Option B: 5-Tier Hierarchy" in result
        assert "Single template per artifact type" in result
        assert "Layered templates with inheritance" in result
        assert "**Pros:**" in result
        assert "- ✅ Simple" in result
        assert "**Cons:**" in result
        assert "- ❌ Duplication" in result

    def test_e2e_concrete_design_chosen_design_section(self) -> None:
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
