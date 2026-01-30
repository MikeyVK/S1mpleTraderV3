# tests/mcp_server/scaffolding/test_tier3_pattern_python_assertions.py
"""
Unit tests for tier3_pattern_python_assertions template.

Tests the Tier 3 assertion pattern block library for pytest-based testing.
Validates that template provides composable blocks for different assertion types:
basic assertions, exception assertions, type assertions, and context assertions.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify tier3_pattern_python_assertions.jinja2 template structure
    - Test block library pattern (no {% extends %}, pure blocks)
    - Validate TEMPLATE_METADATA presence and ARCHITECTURAL enforcement
    - Test 4 assertion pattern blocks: basic, exceptions, type, context
"""

# Standard library
from pathlib import Path

# Third-party
import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment with template loader."""
    templates_dir = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)))


class TestTier3PatternPythonAssertions:
    """Test suite for tier3_pattern_python_assertions template."""

    def test_template_exists(self, jinja_env):
        """Test that tier3_pattern_python_assertions.jinja2 template exists and loads."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        assert template is not None

    def test_template_has_no_extends(self, jinja_env):
        """Test that template follows block library pattern (no {% extends %})."""
        template_path = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates" / "tier3_pattern_python_assertions.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "{% extends" not in content, "Block library should not use {% extends %}"

    def test_template_has_metadata(self, jinja_env):
        """Test that template contains TEMPLATE_METADATA with ARCHITECTURAL enforcement."""
        template_path = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates" / "tier3_pattern_python_assertions.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content, "Template must have TEMPLATE_METADATA"
        assert "enforcement: ARCHITECTURAL" in content, "Template must enforce ARCHITECTURAL rules"

    def test_block_assertions_basic_exists(self, jinja_env):
        """Test that assertions_basic block is defined."""
        template_path = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates" / "tier3_pattern_python_assertions.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_basic %}" in content, "Template must define assertions_basic block"

    def test_block_assertions_exceptions_exists(self, jinja_env):
        """Test that assertions_exceptions block is defined."""
        template_path = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates" / "tier3_pattern_python_assertions.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_exceptions %}" in content, "Template must define assertions_exceptions block"

    def test_block_assertions_type_exists(self, jinja_env):
        """Test that assertions_type block is defined."""
        template_path = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates" / "tier3_pattern_python_assertions.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_type %}" in content, "Template must define assertions_type block"

    def test_block_assertions_context_exists(self, jinja_env):
        """Test that assertions_context block is defined."""
        template_path = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates" / "tier3_pattern_python_assertions.jinja2"
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_context %}" in content, "Template must define assertions_context block"

    def test_import_from_concrete_template(self, jinja_env):
        """Test that template can be extended by concrete templates."""
        # Simulate concrete template extending assertions pattern
        template_str = """
{% extends "tier3_pattern_python_assertions.jinja2" %}

{% block assertions_basic %}
{{ super() }}
# Additional basic assertions
{% endblock %}
"""
        template = jinja_env.from_string(template_str)
        result = template.render()
        assert result is not None, "Template should be extendable"

    def test_assertions_basic_block_contains_equality(self, jinja_env):
        """Test that assertions_basic block contains equality assertion patterns."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        result = template.render()
        # Check for equality patterns
        assert "==" in result or "assert" in result, "Basic assertions should include equality patterns"

    def test_assertions_exceptions_block_contains_pytest_raises(self, jinja_env):
        """Test that assertions_exceptions block contains pytest.raises patterns."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        result = template.render()
        # Check for pytest.raises patterns
        assert "pytest.raises" in result or "exc_info" in result, "Exception assertions should include pytest.raises patterns"

    def test_assertions_type_block_contains_isinstance(self, jinja_env):
        """Test that assertions_type block contains isinstance patterns."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        result = template.render()
        # Check for type checking patterns
        assert "isinstance" in result, "Type assertions should include isinstance patterns"

    def test_assertions_context_block_contains_with_statement(self, jinja_env):
        """Test that assertions_context block contains with statement patterns."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        result = template.render()
        # Check for context manager patterns
        assert "with" in result, "Context assertions should include with statement patterns"
