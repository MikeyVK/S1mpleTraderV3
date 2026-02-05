"""
Task 3.6.1: Comprehensive rendering test for all 5 DOCUMENT templates
Tests that all templates render correctly with tier3 patterns after refactoring.
"""

import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parents[3] / "mcp_server" / "scaffolding" / "templates"


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment with templates loader."""
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def test_planning_md_renders_with_patterns(jinja_env):
    """Test planning.md.jinja2 renders with tier3 status pattern (no collision)."""
    template = jinja_env.get_template("concrete/planning.md.jinja2")
    
    context = {
        "name": "test-planning",
        "title": "Test Planning Document",
        "status": "DRAFT",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "summary": "Test planning summary",
        "tdd_cycles": [
            {
                "name": "Setup",
                "goal": "Create structure",
                "tests": ["Test 1", "Test 2"],
                "success_criteria": ["All pass"]
            }
        ]
    }
    
    output = template.render(**context)
    
    # Verify status field populated (not empty from collision)
    assert "**Status:** DRAFT" in output, "Status field should be populated"
    assert "**Version:** 1.0" in output
    assert "## Summary" in output
    assert "## TDD Cycles" in output


def test_research_md_renders_with_patterns(jinja_env):
    """Test research.md.jinja2 renders with tier3 patterns (status + questions)."""
    template = jinja_env.get_template("concrete/research.md.jinja2")
    
    context = {
        "name": "test-research",
        "title": "Test Research",
        "status": "DRAFT",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "problem_statement": "What is the problem?",
        "findings": ["Finding 1", "Finding 2"],
        "questions_list": [
            {"question": "Question 1", "context": "Context for Q1"},
            {"question": "Question 2", "blocking": True}
        ],
        "references": []
    }
    
    output = template.render(**context)
    
    # Verify status pattern works
    assert "**Status:** DRAFT" in output
    # Verify questions pattern works
    assert "## Open Questions" in output
    assert "Question 1" in output
    assert "Context: Context for Q1" in output or "Question 2" in output


def test_design_md_renders_with_extended_header(jinja_env):
    """Test design.md.jinja2 renders with extended header pattern."""
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
        "context_text": "Design context",
        "requirements": ["Requirement 1"],
        "options": [{"name": "Option A", "description": "Description A"}],
        "chosen_design": "Option A",
        "rationale": "Because reasons",
        "key_decisions": [{"decision": "Decision 1", "rationale": "Rationale 1"}],
        "open_questions_list": [{"question": "Question 1"}]
    }
    
    output = template.render(**context)
    
    # Verify extended header pattern works
    assert "**Status:** APPROVED" in output
    assert "**Created:** 2026-02-01" in output
    assert "**Implementation Phase:**" in output
    # Verify dividers pattern works
    assert output.count("---") >= 4, "Should have multiple dividers"
    # Verify questions pattern works
    assert "## Open Questions" in output or "Question 1" in output


def test_architecture_md_renders_with_numbered_sections(jinja_env):
    """Test architecture.md.jinja2 renders with correct numbering (loop.parent bug fixed)."""
    template = jinja_env.get_template("concrete/architecture.md.jinja2")
    
    context = {
        "name": "test-architecture",
        "title": "Test Architecture",
        "status": "DEFINITIVE",
        "version": "1.0",
        "last_updated": "2026-02-05",
        "timestamp": "2026-02-05T10:00:00",
        "concepts": [
            {
                "name": "Core Concept",
                "description": "This is a core concept",
                "subsections": [
                    {"name": "Subsection 1", "description": "Subsection description"}
                ]
            },
            {
                "name": "Another Concept",
                "description": "Another concept",
                "subsections": []
            }
        ]
    }
    
    output = template.render(**context)
    
    # Verify status works
    assert "**Status:** DEFINITIVE" in output
    # Verify numbered sections work
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
                        "returns": "bool: Success status"
                    }
                ]
            }
        ]
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
