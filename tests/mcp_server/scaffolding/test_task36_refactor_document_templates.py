# tests/mcp_server/scaffolding/test_task36_refactor_document_templates.py
# template=unit_test version=dev created=2026-02-05T23:00Z
"""Task 3.6 validation tests for refactored concrete DOCUMENT templates.

Validates that concrete DOCUMENT templates:
- use {% import %} composition with tier3 patterns
- maintain enforcement: GUIDELINE
- import correct patterns per template
"""

from __future__ import annotations

from pathlib import Path

import pytest


TEMPLATE_ROOT = (
    Path(__file__).parent.parent.parent.parent
    / "mcp_server"
    / "scaffolding"
    / "templates"
    / "concrete"
)


def test_research_md_imports_seven_patterns() -> None:
    """research.md must import 7 tier3 patterns."""
    template_path = TEMPLATE_ROOT / "research.md.jinja2"
    content = template_path.read_text(encoding="utf-8")
    
    # Check for {% import %} or {%- import %} statements
    required_patterns = [
        "tier3_pattern_markdown_status_header",
        "tier3_pattern_markdown_purpose_scope",
        "tier3_pattern_markdown_prerequisites",
        "tier3_pattern_markdown_agent_hints",
        "tier3_pattern_markdown_related_docs",
        "tier3_pattern_markdown_version_history",
        "tier3_pattern_markdown_open_questions",
    ]
    
    for pattern in required_patterns:
        assert 'import "{}.jinja2"'.format(pattern) in content, \
            "research.md missing import: {}".format(pattern)


def test_planning_md_imports_six_patterns() -> None:
    """planning.md must import 6 tier3 patterns."""
    template_path = TEMPLATE_ROOT / "planning.md.jinja2"
    content = template_path.read_text(encoding="utf-8")
    
    required_patterns = [
        "tier3_pattern_markdown_status_header",
        "tier3_pattern_markdown_purpose_scope",
        "tier3_pattern_markdown_prerequisites",
        "tier3_pattern_markdown_agent_hints",
        "tier3_pattern_markdown_related_docs",
        "tier3_pattern_markdown_version_history",
    ]
    
    for pattern in required_patterns:
        assert 'import "{}.jinja2"'.format(pattern) in content, \
            "planning.md missing import: {}".format(pattern)


def test_design_md_imports_seven_patterns() -> None:
    """design.md must import 7 tier3 patterns."""
    template_path = TEMPLATE_ROOT / "design.md.jinja2"
    content = template_path.read_text(encoding="utf-8")
    
    required_patterns = [
        "tier3_pattern_markdown_status_header",
        "tier3_pattern_markdown_purpose_scope",
        "tier3_pattern_markdown_agent_hints",
        "tier3_pattern_markdown_related_docs",
        "tier3_pattern_markdown_version_history",
        "tier3_pattern_markdown_open_questions",
        "tier3_pattern_markdown_dividers",
    ]
    
    for pattern in required_patterns:
        assert 'import "{}.jinja2"'.format(pattern) in content, \
            "design.md missing import: {}".format(pattern)
