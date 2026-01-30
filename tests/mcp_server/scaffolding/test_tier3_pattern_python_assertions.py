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
    templates_dir = (
        Path(__file__).parent.parent.parent.parent
        / "mcp_server"
        / "scaffolding"
        / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_dir)))


class TestTier3PatternPythonAssertions:
    """Test suite for tier3_pattern_python_assertions template."""

    def test_template_exists(self, jinja_env):
        """Test that template exists and loads."""
        template = jinja_env.get_template(
            "tier3_pattern_python_assertions.jinja2"
        )
        assert template is not None

    def test_template_has_no_extends(self):
        """Test that template follows block library pattern."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% extends" not in content

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content

    def test_block_assertions_basic_exists(self):
        """Test that assertions_basic block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_basic %}" in content

    def test_block_assertions_exceptions_exists(
        self,
    ):
        """Test that assertions_exceptions block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_exceptions %}" in content

    def test_block_assertions_type_exists(self):
        """Test that assertions_type block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_type %}" in content

    def test_block_assertions_context_exists(
        self,
    ):
        """Test that assertions_context block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block assertions_context %}" in content

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
        assert result is not None

    def test_assertions_basic_block_contains_equality(self, jinja_env):
        """Test that assertions_basic contains equality patterns."""
        template = jinja_env.get_template(
            "tier3_pattern_python_assertions.jinja2"
        )
        result = template.render()
        assert "==" in result or "assert" in result

    def test_assertions_exceptions_block_contains_pytest_raises(self, jinja_env):
        """Test that assertions_exceptions contains pytest.raises."""
        template = jinja_env.get_template(
            "tier3_pattern_python_assertions.jinja2"
        )
        result = template.render()
        assert "pytest.raises" in result or "exc_info" in result

    def test_assertions_type_block_contains_isinstance(self, jinja_env):
        """Test that assertions_type contains isinstance patterns."""
        template = jinja_env.get_template(
            "tier3_pattern_python_assertions.jinja2"
        )
        result = template.render()
        assert "isinstance" in result

    def test_assertions_context_block_contains_with_statement(self, jinja_env):
        """Test that assertions_context contains with statements."""
        template = jinja_env.get_template(
            "tier3_pattern_python_assertions.jinja2"
        )
        result = template.render()
        assert "with" in result
