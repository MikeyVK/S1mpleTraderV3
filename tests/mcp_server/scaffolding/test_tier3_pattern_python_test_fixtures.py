# tests/mcp_server/scaffolding/test_tier3_pattern_python_test_fixtures.py
"""
Unit tests for tier3_pattern_python_test_fixtures template.

Tests the Tier 3 test fixtures pattern block library for pytest.
Validates that template provides composable blocks for different fixture types:
simple fixtures, generator fixtures, fixture composition, and conftest patterns.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify tier3_pattern_python_test_fixtures.jinja2 template structure
    - Test block library pattern (no {% extends %}, pure blocks)
    - Validate TEMPLATE_METADATA presence and ARCHITECTURAL enforcement
    - Test 4 fixture pattern blocks: simple, generator, composition, conftest
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


class TestTier3PatternPythonTestFixtures:
    """Test suite for tier3_pattern_python_test_fixtures template."""

    def test_template_exists(self, jinja_env):
        """Test that template exists and loads."""
        template = jinja_env.get_template(
            "tier3_pattern_python_test_fixtures.jinja2"
        )
        assert template is not None

    def test_template_has_no_extends(self):
        """Test that template follows block library pattern."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
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
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content

    def test_block_fixtures_simple_exists(self):
        """Test that fixtures_simple block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block fixtures_simple %}" in content

    def test_block_fixtures_generator_exists(self):
        """Test that fixtures_generator block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block fixtures_generator %}" in content

    def test_block_fixtures_composition_exists(self):
        """Test that fixtures_composition block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block fixtures_composition %}" in content

    def test_block_fixtures_conftest_exists(self):
        """Test that fixtures_conftest block is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% block fixtures_conftest %}" in content

    def test_import_from_concrete_template(self, jinja_env):
        """Test that template can be extended by concrete templates."""
        template_str = """
{% extends "tier3_pattern_python_test_fixtures.jinja2" %}

{% block fixtures_simple %}
{{ super() }}
# Additional fixture patterns
{% endblock %}
"""
        template = jinja_env.from_string(template_str)
        result = template.render()
        assert result is not None

    def test_fixtures_simple_block_contains_fixture_decorator(self, jinja_env):
        """Test that fixtures_simple contains @pytest.fixture."""
        template = jinja_env.get_template(
            "tier3_pattern_python_test_fixtures.jinja2"
        )
        result = template.render()
        assert "@pytest.fixture" in result

    def test_fixtures_generator_block_contains_yield(self, jinja_env):
        """Test that fixtures_generator contains yield pattern."""
        template = jinja_env.get_template(
            "tier3_pattern_python_test_fixtures.jinja2"
        )
        result = template.render()
        assert "yield" in result

    def test_fixtures_composition_block_contains_composition(self, jinja_env):
        """Test that fixtures_composition contains fixture composition."""
        template = jinja_env.get_template(
            "tier3_pattern_python_test_fixtures.jinja2"
        )
        result = template.render()
        # Should reference other fixtures in parameters
        assert "fixture" in result.lower()

    def test_fixtures_conftest_block_contains_conftest_pattern(self, jinja_env):
        """Test that fixtures_conftest contains conftest patterns."""
        template = jinja_env.get_template(
            "tier3_pattern_python_test_fixtures.jinja2"
        )
        result = template.render()
        assert "conftest" in result
