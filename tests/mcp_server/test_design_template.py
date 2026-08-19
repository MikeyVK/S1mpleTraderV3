"""Tests for concrete/design.md.jinja2 template.

Tests for full DESIGN_TEMPLATE structure with numbered sections,
options comparison, and key decisions table.

@layer: Tests (Unit)
@dependencies: pytest, jinja2, mcp_server.scaffolding.templates
"""

from jinja2 import Environment, FileSystemLoader, Template

from tests.mcp_server.test_support import get_template_root

_STRUCTURAL = {
    "status": "DRAFT",
    "version": "1.0.0",
    "last_updated": "2026-01-26",
}


def _make_template() -> Template:
    template_dir = get_template_root()
    env = Environment(loader=FileSystemLoader(template_dir))
    return env.get_template("concrete/design.md.jinja2")


class TestDesignTemplateStructure:
    """Tests for design.md.jinja2 full structure."""

    def test_renders_context_and_requirements_section(self) -> None:
        """Design documents must have numbered '1. Context & Requirements' section."""
        template = _make_template()

        result = template.render(
            **_STRUCTURAL,
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

        assert "## 1. Context & Requirements" in result
        assert "### 1.1. Problem Statement" in result
        assert "### 1.2. Requirements" in result
        assert "### 1.3. Constraints" in result
        assert "Test problem" in result

    def test_renders_design_options_section(self) -> None:
        """Design documents must have numbered '2. Design Options' section."""
        template = _make_template()

        result = template.render(
            **_STRUCTURAL,
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

        assert "## 2. Design Options" in result
        assert "### 2.1. Option A: Option A" in result
        assert "### 2.2. Option B: Option B" in result
        assert "Use approach A" in result
        assert "Use approach B" in result
        assert "**Pros:**" in result
        assert "**Cons:**" in result

    def test_renders_chosen_design_section(self) -> None:
        """Design documents must have numbered '3. Chosen Design' section."""
        template = _make_template()

        result = template.render(
            **_STRUCTURAL,
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

        assert "## 3. Chosen Design" in result
        assert "**Decision:**" in result
        assert "**Rationale:**" in result
        assert "Use tiered template architecture" in result
        assert "Provides separation of concerns and reusability" in result
        assert "### 3.1. Key Design Decisions" in result

    def test_renders_key_decisions_table(self) -> None:
        """Design documents must have Key Decisions table with Decision/Rationale columns."""
        template = _make_template()

        result = template.render(
            **_STRUCTURAL,
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

        assert "| Decision | Rationale |" in result
        assert "| Use Jinja2 | Industry standard |" in result
        assert "| Enforce metadata | Quality assurance |" in result

    def test_renders_open_questions_section_when_provided(self) -> None:
        """Design documents can have optional '4. Open Questions' section."""
        template = _make_template()

        result = template.render(
            **_STRUCTURAL,
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

        assert "## 4. Open Questions" in result
        assert "How to handle edge case X?" in result
        assert "Performance impact?" in result

    def test_omits_open_questions_when_not_provided(self) -> None:
        """Open Questions section should not appear if not provided."""
        template = _make_template()

        result = template.render(
            **_STRUCTURAL,
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

        assert "## 4. Open Questions" not in result

    def test_uses_guideline_enforcement_level(self) -> None:
        """Design template should use GUIDELINE enforcement (not STRICT)."""
        template_path = get_template_root() / "concrete" / "design.md.jinja2"
        content = template_path.read_text(encoding="utf-8")

        assert "enforcement: GUIDELINE" in content
        assert "enforcement: STRICT" not in content
