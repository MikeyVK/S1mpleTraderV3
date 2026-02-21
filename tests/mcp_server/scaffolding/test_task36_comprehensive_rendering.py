"""
Task 3.6.1: Comprehensive rendering test for all 5 DOCUMENT templates
Tests that all templates render correctly with tier3 patterns after refactoring.
"""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parents[3] / "mcp_server" / "scaffolding" / "templates"


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment with templates loader."""
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def test_planning_md_renders_with_patterns(jinja_env):
    """Test planning.md.jinja2 renders with ALL tier3 patterns (Task 3.6.2)."""
    template = jinja_env.get_template("concrete/planning.md.jinja2")

    context = {
        "name": "test-planning",
        "title": "Test Planning Document",
        "status": "DRAFT",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "purpose": "This is the purpose of the planning document",
        "scope_in": "Features A, B, C",
        "scope_out": "Features X, Y, Z",
        "prerequisites": ["Read design.md", "Read architecture.md"],
        "related_docs": ["docs/design.md", "docs/research.md"],
        "summary": "Test planning summary",
        "tdd_cycles": [
            {
                "name": "Setup",
                "goal": "Create structure",
                "tests": ["Test 1", "Test 2"],
                "success_criteria": ["All pass"],
            }
        ],
    }

    output = template.render(**context)

    # Verify status field populated (not empty from collision)
    assert "**Status:** DRAFT" in output, "Status field should be populated"
    assert "**Version:** 1.0" in output

    # Verify all 5 tier1 pattern sections from Task 3.6.2
    assert "## Purpose" in output, "Purpose section should render"
    assert "This is the purpose" in output, "Purpose content should render"

    assert "## Scope" in output, "Scope section should render"
    assert "**In Scope:**" in output, "In Scope label should render"
    assert "Features A, B, C" in output, "In scope content should render"
    assert "**Out of Scope:**" in output, "Out of Scope label should render"
    assert "Features X, Y, Z" in output, "Out of scope content should render"

    assert "## Prerequisites" in output, "Prerequisites section should render"
    assert "Read these first:" in output, "Prerequisites text should render"
    assert "Read design.md" in output, "Prerequisite 1 should render"
    assert "Read architecture.md" in output, "Prerequisite 2 should render"

    assert "## Related Documentation" in output, "Related docs section should render"
    assert "[docs/design.md][related-1]" in output, "Related doc 1 link ref should render"
    assert "[docs/research.md][related-2]" in output, "Related doc 2 link ref should render"

    assert "## Version History" in output, "Version history section should render"
    assert "| Version | Date | Author | Changes |" in output, (
        "Version history table header (4 columns) should render"
    )
    assert "| Agent |" in output, "Version history Agent column should render"

    # Verify planning-specific content
    assert "## Summary" in output
    assert "## TDD Cycles" in output


def test_research_md_renders_with_patterns(jinja_env):
    """Test research.md.jinja2 renders with ALL tier3 patterns (Task 3.6.2)."""
    template = jinja_env.get_template("concrete/research.md.jinja2")

    context = {
        "name": "test-research",
        "title": "Test Research",
        "status": "DRAFT",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "purpose": "Research purpose text",
        "scope_in": "Research scope in",
        "scope_out": "Research scope out",
        "prerequisites": ["Read prerequisite 1"],
        "problem_statement": "What is the problem?",
        "goals": ["Goal 1", "Goal 2"],
        "findings": "Research findings text",
        "questions_list": [
            {"question": "Question 1", "context": "Context for Q1"},
            {"question": "Question 2", "blocking": True},
        ],
        "references": ["docs/architecture.md", "docs/planning.md"],
    }

    output = template.render(**context)

    # Verify status pattern works
    assert "**Status:** DRAFT" in output

    # Verify all 5 tier1 pattern sections from Task 3.6.2
    assert "## Purpose" in output, "Purpose section should render"
    assert "Research purpose text" in output, "Purpose content should render"

    assert "## Scope" in output, "Scope section should render"
    assert "**In Scope:**" in output, "In Scope label should render"
    assert "Research scope in" in output, "In scope content should render"
    assert "**Out of Scope:**" in output, "Out of Scope label should render"
    assert "Research scope out" in output, "Out of scope content should render"

    assert "## Prerequisites" in output, "Prerequisites section should render"
    assert "Read these first:" in output, "Prerequisites text should render"
    assert "Read prerequisite 1" in output, "Prerequisite should render"

    # Related docs uses 'references' context variable for research.md
    assert "## Related Documentation" in output, "Related docs section should render"
    assert "[docs/architecture.md][related-1]" in output, "Reference 1 link ref should render"
    assert "[docs/planning.md][related-2]" in output, "Reference 2 link ref should render"

    assert "## Version History" in output, "Version history section should render"
    assert "| Version | Date | Author | Changes |" in output, (
        "Version history table header (4 columns) should render"
    )
    assert "| Agent |" in output, "Version history Agent column should render"

    # Verify research-specific content (questions pattern works)
    assert "## Open Questions" in output
    assert "Question 1" in output
    assert "Context: Context for Q1" in output or "Question 2" in output


def test_design_md_renders_with_extended_header(jinja_env):
    """Test design.md.jinja2 renders with extended header + ALL tier3 patterns (Task 3.6.2)."""
    template = jinja_env.get_template("concrete/design.md.jinja2")

    context = {
        "name": "test-design",
        "title": "Test Design",
        "status": "APPROVED",
        "version": "2.0",
        "created": "2026-02-01",
        "last_updated": "2026-02-05",
        "implementation_phase": "design",
        "timestamp": "2026-02-05T10:00:00",
        "purpose": "Design purpose text",
        "scope_in": "Design scope in",
        "scope_out": "Design scope out",
        "prerequisites": ["Read planning.md", "Read research.md"],
        "related_docs": ["docs/planning.md", "docs/architecture.md"],
        "problem_statement": "Design problem",
        "requirements_functional": ["Requirement 1"],
        "requirements_nonfunctional": ["Non-functional 1"],
        "options": [
            {
                "name": "Option A",
                "description": "Description A",
                "pros": ["Pro1"],
                "cons": ["Con1"],
            }
        ],
        "decision": "Option A",
        "rationale": "Because reasons",
        "key_decisions": [{"decision": "Decision 1", "rationale": "Rationale 1"}],
        "open_questions_list": [{"question": "Question 1"}],
    }

    output = template.render(**context)

    # Verify basic header pattern works (created/implementation_phase removed per Issue #5)
    assert "**Status:** APPROVED" in output
    assert "**Version:** 2.0" in output
    assert "**Last Updated:** 2026-02-05" in output

    # Verify all 5 tier1 pattern sections from Task 3.6.2
    assert "## Purpose" in output, "Purpose section should render"
    assert "Design purpose text" in output, "Purpose content should render"

    assert "## Scope" in output, "Scope section should render"
    assert "**In Scope:**" in output, "In Scope label should render"
    assert "Design scope in" in output, "In scope content should render"
    assert "**Out of Scope:**" in output, "Out of Scope label should render"
    assert "Design scope out" in output, "Out of scope content should render"

    assert "## Prerequisites" in output, "Prerequisites section should render"
    assert "Read these first:" in output, "Prerequisites text should render"
    assert "Read planning.md" in output, "Prerequisite 1 should render"
    assert "Read research.md" in output, "Prerequisite 2 should render"

    assert "## Related Documentation" in output, "Related docs section should render"
    assert "[docs/planning.md][related-1]" in output, "Related doc 1 link ref should render"
    assert "[docs/architecture.md][related-2]" in output, "Related doc 2 link ref should render"

    assert "## Version History" in output, "Version history section should render"
    assert "| Version | Date | Author | Changes |" in output, (
        "Version history table header (4 columns) should render"
    )
    assert "| Agent |" in output, "Version history Agent column should render"

    # Verify design-specific content
    assert output.count("---") >= 4, "Should have multiple dividers"
    assert "## Open Questions" in output or "Question 1" in output


def test_architecture_md_renders_with_numbered_sections(jinja_env):
    """Test architecture.md.jinja2 renders with numbering + ALL tier3 patterns (Task 3.6.2)."""
    template = jinja_env.get_template("concrete/architecture.md.jinja2")

    context = {
        "name": "test-architecture",
        "title": "Test Architecture",
        "status": "DEFINITIVE",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "purpose": "Architecture purpose text",
        "scope_in": "Architecture scope in",
        "scope_out": "Architecture scope out",
        "prerequisites": ["Read design.md"],
        "related_docs": ["docs/design.md", "docs/research.md"],
        "concepts": [
            {
                "name": "Core Concept",
                "description": "This is a core concept",
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "description": "Subsection description",
                    }
                ],
            },
            {"name": "Another Concept", "description": "Another concept", "subsections": []},
        ],
    }

    output = template.render(**context)

    # Verify status works
    assert "**Status:** DEFINITIVE" in output

    # Verify all 5 tier1 pattern sections from Task 3.6.2
    assert "## Purpose" in output, "Purpose section should render"
    assert "Architecture purpose text" in output, "Purpose content should render"

    assert "## Scope" in output, "Scope section should render"
    assert "**In Scope:**" in output, "In Scope label should render"
    assert "Architecture scope in" in output, "In scope content should render"
    assert "**Out of Scope:**" in output, "Out of Scope label should render"
    assert "Architecture scope out" in output, "Out of scope content should render"

    assert "## Prerequisites" in output, "Prerequisites section should render"
    assert "Read these first:" in output, "Prerequisites text should render"
    assert "Read design.md" in output, "Prerequisite should render"

    assert "## Related Documentation" in output, "Related docs section should render"
    assert "[docs/design.md][related-1]" in output, "Related doc 1 link ref should render"
    assert "[docs/research.md][related-2]" in output, "Related doc 2 link ref should render"

    assert "## Version History" in output, "Version history section should render"
    assert "| Version | Date | Author | Changes |" in output, (
        "Version history table header (4 columns) should render"
    )
    assert "| Agent |" in output, "Version history Agent column should render"

    # Verify architecture-specific content (numbered sections work)
    assert "## 1. Core Concept" in output
    assert "## 2. Another Concept" in output
    # Verify subsection numbering works (loop.parent bug fixed)
    assert "### 1.1. Subsection 1" in output


def test_reference_md_renders_with_custom_header(jinja_env):
    """Test reference.md.jinja2 renders with custom header (Source/Tests fields)."""
    template = jinja_env.get_template("concrete/reference.md.jinja2")

    context = {
        "name": "test-reference",
        "title": "Test Reference",
        "status": "DEFINITIVE",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "source_file": "src/module.py",
        "test_file": "tests/test_module.py",
        "test_count": 10,
        "api_reference": [
            {
                "name": "MyClass",
                "description": "A test class",
                "methods": [
                    {
                        "signature": "do_thing(param: str) -> bool",
                        "params": "param: Input string",
                        "returns": "bool: Success status",
                    }
                ],
            }
        ],
    }

    output = template.render(**context)

    # Verify custom header works
    assert "**Status:** DEFINITIVE" in output
    assert "**Source:** [src/module.py]" in output
    assert "**Tests:** [tests/test_module.py]" in output
    assert "(10 tests)" in output
    # Verify API reference section works
    assert "## API Reference" in output
    assert "### MyClass" in output
