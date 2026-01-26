"""Test concrete/design.md.jinja2 template (TDD Cycle 5).

Tests for full DESIGN_TEMPLATE structure with numbered sections,
options comparison, and key decisions table.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader


class TestDesignTemplateStructure:
    """Test design.md.jinja2 full structure (Cycle 5)."""

    def test_renders_context_and_requirements_section(self):
        """Design documents must have numbered '1. Context & Requirements' section."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            title="Test Design",
            purpose="Test design template",
            scope_in="X",
            scope_out="Y",
            timestamp="2026-01-26T10:00:00Z",
            artifact_type="design",
            version_hash="abc123",
            output_path="docs/design.md",
            format="markdown",
            problem_statement="Test problem",
            requirements="Test requirements",
            constraints="None",
            options=[],
            decision="Test decision",
            rationale="Test rationale",
            key_decisions=[],
        )

        # Section 1 must exist with Problem/Requirements/Constraints subsections
        assert "## 1. Context & Requirements" in result
        assert "### Problem Statement" in result
        assert "### Requirements" in result
        assert "### Constraints" in result
        assert "Test problem" in result
        assert "Test requirements" in result

    def test_renders_design_options_section(self):
        """Design documents must have numbered '2. Design Options' section."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            timestamp="2026-01-26T10:00:00Z",
            artifact_type="design",
            version_hash="abc123",
            output_path="docs/design.md",
            format="markdown",
            problem_statement="Problem",
            requirements="Requirements",
            options=[
                {
                    "name": "Option A",
                    "description": "Use approach A",
                    "pros": ["Pro 1", "Pro 2"],
                    "cons": ["Con 1"],
                },
                {
                    "name": "Option B",
                    "description": "Use approach B",
                    "pros": ["Pro X"],
                    "cons": ["Con X", "Con Y"],
                },
            ],
            decision="Choose A",
            rationale="Best fit",
            key_decisions=[],
        )

        # Section 2 must exist with option subsections
        assert "## 2. Design Options" in result
        assert "### Option 1: Option A" in result
        assert "### Option 2: Option B" in result
        assert "Use approach A" in result
        assert "Use approach B" in result
        assert "**Pros:**" in result
        assert "**Cons:**" in result

    def test_renders_chosen_design_section(self):
        """Design documents must have numbered '3. Chosen Design' section."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            timestamp="2026-01-26T10:00:00Z",
            artifact_type="design",
            version_hash="abc123",
            output_path="docs/design.md",
            format="markdown",
            problem_statement="Problem",
            requirements="Requirements",
            options=[],
            decision="Use tiered template architecture",
            rationale="Provides separation of concerns and reusability",
            key_decisions=[
                {
                    "decision": "5-tier hierarchy",
                    "rationale": "Clear separation",
                    "tradeoffs": "More complexity",
                },
            ],
        )

        # Section 3 must exist with Decision/Rationale/Key Decisions
        assert "## 3. Chosen Design" in result
        assert "### Decision" in result
        assert "### Rationale" in result
        assert "Use tiered template architecture" in result
        assert "Provides separation of concerns and reusability" in result
        assert "### Key Decisions" in result

    def test_renders_key_decisions_table(self):
        """Design documents must have Key Decisions table with Decision/Rationale/Trade-offs."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            timestamp="2026-01-26T10:00:00Z",
            artifact_type="design",
            version_hash="abc123",
            output_path="docs/design.md",
            format="markdown",
            problem_statement="Problem",
            requirements="Requirements",
            options=[],
            decision="Decision",
            rationale="Rationale",
            key_decisions=[
                {
                    "decision": "Use Jinja2",
                    "rationale": "Industry standard",
                    "tradeoffs": "Learning curve",
                },
                {
                    "decision": "Enforce metadata",
                    "rationale": "Quality assurance",
                    "tradeoffs": "More boilerplate",
                },
            ],
        )

        # Key Decisions table must have proper columns
        assert "| Decision | Rationale | Trade-offs |" in result
        assert "| Use Jinja2 | Industry standard | Learning curve |" in result
        assert "| Enforce metadata | Quality assurance | More boilerplate |" in result

    def test_renders_open_questions_section_when_provided(self):
        """Design documents can have optional '4. Open Questions' section."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            timestamp="2026-01-26T10:00:00Z",
            artifact_type="design",
            version_hash="abc123",
            output_path="docs/design.md",
            format="markdown",
            problem_statement="Problem",
            requirements="Requirements",
            options=[],
            decision="Decision",
            rationale="Rationale",
            key_decisions=[],
            open_questions=["How to handle edge case X?", "Performance impact?"],
        )

        # Open questions section is optional
        assert "## 4. Open Questions" in result
        assert "How to handle edge case X?" in result
        assert "Performance impact?" in result

    def test_omits_open_questions_when_not_provided(self):
        """Open Questions section should not appear if not provided."""
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("concrete/design.md.jinja2")

        result = template.render(
            title="Test Design",
            purpose="Test",
            scope_in="X",
            scope_out="Y",
            timestamp="2026-01-26T10:00:00Z",
            artifact_type="design",
            version_hash="abc123",
            output_path="docs/design.md",
            format="markdown",
            problem_statement="Problem",
            requirements="Requirements",
            options=[],
            decision="Decision",
            rationale="Rationale",
            key_decisions=[],
        )

        # No open questions section
        assert "## 4. Open Questions" not in result

    def test_uses_guideline_enforcement_level(self):
        """Design template should use GUIDELINE enforcement (not STRICT)."""
        template_path = Path("mcp_server/scaffolding/templates/concrete/design.md.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Check TEMPLATE_METADATA for enforcement: GUIDELINE
        assert "enforcement: GUIDELINE" in content
        assert "enforcement: STRICT" not in content
