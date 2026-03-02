"""
Task 3.6.1: Test tier1_base_document.jinja2 refactor
Tests that tier1_base_document has all required composable blocks for tier3 pattern injection.

TDD Phase: RED → GREEN
"""

from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).parents[3] / "mcp_server" / "scaffolding" / "templates"
TIER1_BASE_DOC = TEMPLATES_DIR / "tier1_base_document.jinja2"


@pytest.fixture
def tier1_base_document():
    """Load tier1_base_document.jinja2 content."""
    assert TIER1_BASE_DOC.exists(), f"tier1_base_document not found at {TIER1_BASE_DOC}"
    return TIER1_BASE_DOC.read_text(encoding="utf-8")


def test_tier1_base_document_has_purpose_block(tier1_base_document):
    """
    Test that tier1_base_document has purpose_section block.
    This enables tier3 patterns to inject custom purpose content.
    """
    content = tier1_base_document
    assert "block purpose_section" in content, "tier1_base_document missing purpose_section block"


def test_tier1_base_document_has_scope_block(tier1_base_document):
    """
    Test that tier1_base_document has scope_section block.
    This enables tier3 patterns to inject custom scope content.
    """
    content = tier1_base_document
    assert "block scope_section" in content, "tier1_base_document missing scope_section block"


def test_tier1_base_document_has_prerequisites_block(tier1_base_document):
    """
    Test that tier1_base_document has prerequisites_section block.
    This enables tier3 patterns to inject custom prerequisites content.
    """
    content = tier1_base_document
    assert "block prerequisites_section" in content, (
        "tier1_base_document missing prerequisites_section block"
    )


def test_tier1_base_document_has_related_docs_block(tier1_base_document):
    """
    Test that tier1_base_document has related_docs_section block.
    This enables tier3 patterns to inject custom related docs content.
    """
    content = tier1_base_document
    assert "block related_docs_section" in content, (
        "tier1_base_document missing related_docs_section block"
    )


def test_tier1_base_document_has_version_history_block(tier1_base_document):
    """
    Test that tier1_base_document has version_history_section block.
    This enables tier3 patterns to inject custom version history content.
    """
    content = tier1_base_document
    assert "block version_history_section" in content, (
        "tier1_base_document missing version_history_section block"
    )
