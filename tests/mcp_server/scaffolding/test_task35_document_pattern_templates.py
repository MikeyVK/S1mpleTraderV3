# tests/mcp_server/scaffolding/test_task35_document_pattern_templates.py
# template=unit_test version=dev created=2026-02-05T21:00Z updated=
"""Task 3.5 validation tests for tier3 markdown pattern templates.

Validates that tier3 markdown pattern templates:
- exist in the templates directory
- provide expected macro exports

Step 1 (TDD Cycle 1): test for tier3_pattern_markdown_status_header.jinja2
Step 2 (TDD Cycle 2): test for tier3_pattern_markdown_purpose_scope.jinja2
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
    """RED: tier3_pattern_markdown_purpose_scope.jinja2 must exist."""
    template_path = TEMPLATE_ROOT / "tier3_pattern_markdown_purpose_scope.jinja2"
    assert template_path.exists(), "tier3_pattern_markdown_purpose_scope.jinja2 not found"
