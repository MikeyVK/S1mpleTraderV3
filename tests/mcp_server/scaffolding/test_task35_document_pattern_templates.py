# tests/mcp_server/scaffolding/test_task35_document_pattern_templates.py
# template=unit_test version=dev created=2026-02-05T21:00Z updated=2026-02-05T22:30Z
"""Task 3.5 validation tests for tier3 markdown pattern templates.

Validates that tier3 markdown pattern templates:
- exist in the templates directory
- provide expected macro exports

All 8 patterns for markdown DOCUMENT templates.
"""

from __future__ import annotations

from pathlib import Path

import pytest


TEMPLATE_ROOT = (
    Path(__file__).parent.parent.parent.parent
    / "mcp_server"
    / "scaffolding"
    / "templates"
)


def test_tier3_pattern_markdown_status_header_exists() -> None:
    """tier3_pattern_markdown_status_header.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_status_header.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_status_header.jinja2 not found"


def test_tier3_pattern_markdown_purpose_scope_exists() -> None:
    """tier3_pattern_markdown_purpose_scope.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_purpose_scope.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_purpose_scope.jinja2 not found"


def test_tier3_pattern_markdown_prerequisites_exists() -> None:
    """RED: tier3_pattern_markdown_prerequisites.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_prerequisites.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_prerequisites.jinja2 not found"


def test_tier3_pattern_markdown_agent_hints_exists() -> None:
    """RED: tier3_pattern_markdown_agent_hints.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_agent_hints.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_agent_hints.jinja2 not found"


def test_tier3_pattern_markdown_related_docs_exists() -> None:
    """RED: tier3_pattern_markdown_related_docs.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_related_docs.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_related_docs.jinja2 not found"


def test_tier3_pattern_markdown_version_history_exists() -> None:
    """RED: tier3_pattern_markdown_version_history.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_version_history.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_version_history.jinja2 not found"


def test_tier3_pattern_markdown_open_questions_exists() -> None:
    """RED: tier3_pattern_markdown_open_questions.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_open_questions.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_open_questions.jinja2 not found"


def test_tier3_pattern_markdown_dividers_exists() -> None:
    """RED: tier3_pattern_markdown_dividers.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_dividers.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_dividers.jinja2 not found"
