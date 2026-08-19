"""Integration tests for concrete document templates (research, planning, architecture, reference).

Tests verify:
- Template structure matches BASE_TEMPLATE.md
- Multi-line header fields (Status, Version, Last Updated)
- Dividers have blank lines before and after
- No frontmatter (removed per BASE_TEMPLATE alignment)
- Title fallback to name parameter
- Proper whitespace control (no excessive blank lines)

@layer: Tests (Integration)
@dependencies: [pytest, pathlib, jinja2]
"""

import pytest
from jinja2 import Environment, FileSystemLoader, Template

from tests.mcp_server.test_support import get_template_root

_DOC_HEADER = {
    "status": "DRAFT",
    "version": "1.0.0",
    "last_updated": "2026-01-27",
}

_REFERENCE_HEADER = {
    "status": "DEFINITIVE",
    "version": "1.0.0",
    "last_updated": "2026-01-27",
}


class TestResearchTemplate:
    """Test concrete/research.md.jinja2 structure and rendering."""

    @pytest.fixture
    def template(self) -> Template:
        """Load research template."""
        template_dir = get_template_root()
        env = Environment(loader=FileSystemLoader(template_dir))
        return env.get_template("concrete/research.md.jinja2")

    def test_has_title_from_name_fallback(self, template: Template) -> None:
        """Research doc should use 'name' parameter if 'title' not provided."""
        result = template.render(
            name="async-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Problem",
            goals=["Goal 1"],
        )

        # Title should fallback to name
        assert "# async-research" in result

    def test_has_multiline_header_fields(self, template: Template) -> None:
        """Header fields must be multi-line (Status, Version, Last Updated)."""
        result = template.render(
            name="test-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Problem",
            goals=["Goal 1"],
            **_DOC_HEADER,
        )
        # Multi-line header fields (not frontmatter)
        assert "**Status:** DRAFT" in result
        assert "**Version:** 1.0" in result
        assert "**Last Updated:** 2026-01-27" in result

    def test_no_frontmatter(self, template: Template) -> None:
        """Research template must NOT have YAML frontmatter."""
        result = template.render(
            name="test-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Problem",
            goals=["Goal 1"],
        )

        lines = result.split("\n")
        # After comment headers, first non-comment line should be title
        non_comment_lines = [line for line in lines if not line.startswith("<!--")]
        assert non_comment_lines[0].startswith("# ")

    def test_has_proper_dividers_with_blank_lines(self, template: Template) -> None:
        """Dividers (---) must have blank line before AND after."""
        result = template.render(
            name="test-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Test problem",
            goals=["Goal 1", "Goal 2"],
            background="Background info",
            findings="Some findings",
            questions=["Question 1"],
            references=["https://example.com"],
        )

        lines = result.split("\n")

        # Find all divider lines
        divider_indices = [i for i, line in enumerate(lines) if line.strip() == "---"]

        # Each divider must have blank line before and after
        for idx in divider_indices:
            assert not lines[idx - 1].strip(), f"Missing blank line before divider at line {idx}"
            assert not lines[idx + 1].strip(), f"Missing blank line after divider at line {idx}"

    def test_renders_problem_statement(self, template: Template) -> None:
        """Research doc must render problem statement."""
        result = template.render(
            name="test-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Async data fetching is slow",
            goals=["Goal 1"],
        )

        assert "## Problem Statement" in result
        assert "Async data fetching is slow" in result

    def test_renders_research_goals_as_list(self, template: Template) -> None:
        """Research goals must render as bullet list."""
        result = template.render(
            name="test-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Problem",
            goals=["Understand async patterns", "Evaluate WebSocket"],
        )

        assert "## Research Goals" in result
        assert "- Understand async patterns" in result
        assert "- Evaluate WebSocket" in result

    def test_renders_open_questions_with_emoji(self, template: Template) -> None:
        """Open questions must render with the question-mark emoji."""
        result = template.render(
            name="test-research",
            timestamp="2026-01-27T14:00:00Z",
            problem_statement="Problem",
            goals=["Goal 1"],
            questions=["What is optimal pool size?", "How to reconnect?"],
        )

        assert "## Open Questions" in result
        assert "- \u2753 What is optimal pool size?" in result
        assert "- \u2753 How to reconnect?" in result


class TestPlanningTemplate:
    """Test concrete/planning.md.jinja2 structure and rendering."""

    @pytest.fixture
    def template(self) -> Template:
        """Load planning template."""
        template_dir = get_template_root()
        env = Environment(loader=FileSystemLoader(template_dir))
        return env.get_template("concrete/planning.md.jinja2")

    def test_has_multiline_header_fields(self, template: Template) -> None:
        """Planning doc must have multi-line header fields."""
        result = template.render(
            name="test-planning",
            timestamp="2026-01-27T15:00:00Z",
            summary="Test planning",
            cycles=[],
            **_DOC_HEADER,
        )
        assert "**Status:** DRAFT" in result
        assert "**Version:** 1.0" in result
        assert "**Last Updated:** 2026-01-27" in result

    def test_renders_cycles(self, template: Template) -> None:
        """Planning doc must render TDD cycles with Goal/Tests/Success Criteria."""
        result = template.render(
            name="test-planning",
            timestamp="2026-01-27T15:00:00Z",
            summary="Test",
            cycles=[
                {
                    "goal": "Create async client",
                    "tests": ["test_client_creation", "test_async_fetch"],
                    "success_criteria": "Client fetches data async",
                }
            ],
        )

        assert "## TDD Cycles" in result
        assert "### Cycle 1:" in result
        assert "**Goal:** Create async client" in result
        assert "**Tests:**" in result
        assert "- test_client_creation" in result
        assert "**Success Criteria:**" in result
        assert "Client fetches data async" in result

    def test_success_criteria_handles_string(self, template: Template) -> None:
        """Success criteria should handle string (not iterate characters)."""
        result = template.render(
            name="test-planning",
            timestamp="2026-01-27T15:00:00Z",
            summary="Test",
            cycles=[
                {
                    "goal": "Test",
                    "tests": ["test1"],
                    "success_criteria": "This is a single string",
                }
            ],
        )

        # Should NOT split into individual characters
        assert "This is a single string" in result
        assert "- T" not in result  # Would appear if iterating string

    def test_success_criteria_handles_list(self, template: Template) -> None:
        """Success criteria should handle list of criteria."""
        result = template.render(
            name="test-planning",
            timestamp="2026-01-27T15:00:00Z",
            summary="Test",
            cycles=[
                {
                    "goal": "Test",
                    "tests": ["test1"],
                    "success_criteria": ["Criteria 1", "Criteria 2"],
                }
            ],
        )

        assert "- Criteria 1" in result
        assert "- Criteria 2" in result


class TestArchitectureTemplate:
    """Test concrete/architecture.md.jinja2 structure and rendering."""

    @pytest.fixture
    def template(self) -> Template:
        """Load architecture template."""
        template_dir = get_template_root()
        env = Environment(loader=FileSystemLoader(template_dir))
        return env.get_template("concrete/architecture.md.jinja2")

    def test_has_multiline_header_fields(self, template: Template) -> None:
        """Architecture doc must have multi-line header fields."""
        result = template.render(
            name="test-architecture",
            timestamp="2026-01-27T15:00:00Z",
            concepts=[],
            **_DOC_HEADER,
        )
        assert "**Status:** DRAFT" in result
        assert "**Version:** 1.0" in result
        assert "**Last Updated:** 2026-01-27" in result

    def test_renders_numbered_concept_sections(self, template: Template) -> None:
        """Architecture concepts must render as numbered sections (1., 2., etc.)."""
        result = template.render(
            name="test-architecture",
            timestamp="2026-01-27T15:00:00Z",
            concepts=[
                {"name": "AsyncManager", "description": "Manages async operations"},
                {"name": "ConnectionPool", "description": "Pool of connections"},
            ],
        )

        assert "## 1. AsyncManager" in result
        assert "Manages async operations" in result
        assert "## 2. ConnectionPool" in result
        assert "Pool of connections" in result

    def test_renders_constraints_and_decisions_table(self, template: Template) -> None:
        """Architecture doc must render Constraints & Decisions table."""
        result = template.render(
            name="test-architecture",
            timestamp="2026-01-27T15:00:00Z",
            concepts=[],
            decisions=[
                {
                    "decision": "Use aiohttp",
                    "rationale": "Battle-tested",
                    "alternatives": "httpx",
                }
            ],
        )

        assert "## Constraints & Decisions" in result
        assert "| Decision | Rationale | Alternatives Rejected |" in result
        assert "| Use aiohttp | Battle-tested | httpx |" in result


class TestReferenceTemplate:
    """Test concrete/reference.md.jinja2 structure and rendering."""

    @pytest.fixture
    def template(self) -> Template:
        """Load reference template."""
        template_dir = get_template_root()
        env = Environment(loader=FileSystemLoader(template_dir))
        return env.get_template("concrete/reference.md.jinja2")

    def test_has_definitive_status(self, template: Template) -> None:
        """Reference docs are always DEFINITIVE (post-implementation)."""
        result = template.render(
            name="test-reference",
            timestamp="2026-01-27T15:00:00Z",
            source_file="src/test.py",
            test_file="tests/test_test.py",
            **_REFERENCE_HEADER,
            api_reference=[],
        )

        assert "**Status:** DEFINITIVE" in result

    def test_has_source_and_test_links(self, template: Template) -> None:
        """Reference docs must have Source and Tests header fields."""
        result = template.render(
            name="test-reference",
            timestamp="2026-01-27T15:00:00Z",
            source_file="src/async_client.py",
            test_file="tests/test_async_client.py",
            api_reference=[],
        )

        assert "**Source:** [src/async_client.py][source]" in result
        assert "**Tests:** [tests/test_async_client.py][tests]" in result

    def test_renders_api_reference_with_methods(self, template: Template) -> None:
        """API reference must render classes with methods."""
        result = template.render(
            name="test-reference",
            timestamp="2026-01-27T15:00:00Z",
            source_file="src/test.py",
            test_file="tests/test.py",
            api_reference=[
                {
                    "name": "AsyncClient",
                    "description": "Async HTTP client",
                    "methods": [
                        {
                            "signature": "async def fetch(url: str) -> Response",
                            "params": "url: str",
                            "returns": "Response",
                        }
                    ],
                }
            ],
        )

        assert "### AsyncClient" in result
        assert "Async HTTP client" in result
        assert "**Methods:**" in result
        assert "`async def fetch(url: str) -> Response`" in result
        assert "**Parameters:** url: str" in result
        assert "**Returns:** Response" in result

    def test_renders_usage_examples_with_code_blocks(self, template: Template) -> None:
        """Usage examples must render with Python code blocks."""
        result = template.render(
            name="test-reference",
            timestamp="2026-01-27T15:00:00Z",
            source_file="src/test.py",
            test_file="tests/test.py",
            api_reference=[],
            usage_examples=[
                {
                    "description": "Basic fetch",
                    "code": "client = AsyncClient()\ndata = await client.fetch('url')",
                }
            ],
        )

        assert "## Usage Examples" in result
        assert "**Basic fetch**" in result
        assert "```python" in result
        assert "client = AsyncClient()" in result
        assert "data = await client.fetch('url')" in result
