"""Test suite for generic document template.

Tests verify that the generic.md.jinja2 template renders correctly with:
- Minimal required fields (title, purpose, issue)- Optional sections (related_docs, scope, custom sections)
- Front matter metadata formatting
"""

from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


@pytest.fixture
def template_env() -> Environment:
    """Create Jinja2 environment with templates directory."""
    template_dir = Path(__file__).parent.parent.parent.parent / "mcp_server" / "templates"
    return Environment(loader=FileSystemLoader(template_dir))


@pytest.fixture
def minimal_context() -> dict[str, Any]:
    """Minimal context for generic document - only required fields."""
    return {
        "title": "Migration Guide: v1.x → v2.0",
        "purpose": "Provide comprehensive upgrade path from legacy to new system",
        "issue_number": 138,
    }


@pytest.fixture
def full_context() -> dict[str, Any]:
    """Full context with all optional fields."""
    return {
        "title": "Migration Guide: v1.x → v2.0",
        "purpose": "Provide comprehensive upgrade path from legacy to new system",
        "issue_number": 138,
        "date": "2026-02-16",
        "breaking_changes": "Yes (but backward compatible until v3.0)",
        "scope_in": "Backward compat, auto-detect, explicit syntax",
        "scope_out": "Internal implementation, performance tuning",
        "related_docs": ["agent.md", "CHANGELOG.md"],
        "custom_sections": [
            {"heading": "Migration Paths", "content": "Three migration options available"},
            {"heading": "Syntax Comparison", "content": "Old vs new syntax examples"},
            {"heading": "FAQ", "content": "Common questions and answers"}
        ]
    }


class TestGenericDocTemplate:
    """Test suite for generic.md.jinja2 template."""

    def test_minimal_generic_doc_with_only_required_fields(
        self, 
        template_env: Environment,
        minimal_context: dict[str, Any]
    ) -> None:
        """Verify generic doc renders with minimal required fields.
        
        Test verifies:
        - Title rendered correctly (H1)
        - Issue metadata present
        - Purpose section rendered
        - No optional sections appear
        """
        # Arrange: Load template
        template = template_env.get_template("concrete/generic.md.jinja2")
        
        # Act: Render with minimal context
        result = template.render(**minimal_context)
        
        # Assert: Required elements present
        assert "# Migration Guide: v1.x → v2.0" in result
        assert "**Issue:** #138" in result
        assert "## Purpose" in result
        assert "Provide comprehensive upgrade path" in result
        
        # Assert: Optional elements NOT present
        assert "**Date:**" not in result
        assert "**Breaking Changes:**" not in result
        assert "## Scope" not in result
        assert "## Related Documentation" not in result

    def test_generic_doc_with_custom_sections(
        self,
        template_env: Environment,
        full_context: dict[str, Any]
    ) -> None:
        """Verify generic doc renders user-defined custom sections in order.
        
        Test verifies:
        - All custom section headers present
        - Sections appear in specified order
        - Section content rendered correctly
        - Optional front matter included
        """
        # Arrange: Load template
        template = template_env.get_template("concrete/generic.md.jinja2")
        
        # Act: Render with full context including custom sections
        result = template.render(**full_context)
        
        # Assert: Front matter optional fields present
        assert "**Date:** 2026-02-16" in result
        assert "**Breaking Changes:** Yes (but backward compatible until v3.0)" in result
        
        # Assert: Scope sections present
        assert "## Scope" in result
        assert "**In Scope:**" in result
        assert "Backward compat, auto-detect, explicit syntax" in result
        assert "**Out of Scope:**" in result
        assert "Internal implementation, performance tuning" in result
        
        # Assert: Related docs present
        assert "## Related Documentation" in result
        assert "- [agent.md](agent.md)" in result
        assert "- [CHANGELOG.md](CHANGELOG.md)" in result
        
        # Assert: Custom sections in correct order
        migration_pos = result.index("## Migration Paths")
        syntax_pos = result.index("## Syntax Comparison")
        faq_pos = result.index("## FAQ")
        assert migration_pos < syntax_pos < faq_pos
        
        # Assert: Custom section content present
        assert "Three migration options available" in result
        assert "Old vs new syntax examples" in result
        assert "Common questions and answers" in result
