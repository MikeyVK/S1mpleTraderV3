"""Unit tests for tier3_pattern_python_pytest.jinja2 block library.

Tests the pytest framework pattern blocks used by test_unit and test_integration templates.
This is a BLOCK LIBRARY template (no {% extends %}), provides composable blocks only.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Validate pytest pattern block structure
    - Test fixture decorators (@pytest.fixture)
    - Test async markers (@pytest.mark.asyncio)
    - Test parametrize decorators (@pytest.mark.parametrize)
    - Test pytest_plugins configuration
"""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment for template testing."""
    template_dir = Path("mcp_server/scaffolding/templates")
    return Environment(loader=FileSystemLoader(template_dir))


class TestTier3PatternPythonPytest:
    """Test pytest pattern blocks for composition via {% import %}."""

    def test_template_exists(self, jinja_env):
        """RED: Verify tier3_pattern_python_pytest.jinja2 exists and loads."""
        template = jinja_env.get_template("tier3_pattern_python_pytest.jinja2")
        assert template is not None
        assert "tier3_pattern_python_pytest.jinja2" in template.name

    def test_template_has_no_extends(self):
        """RED: Verify template is a BLOCK LIBRARY (no {% extends %} statement)."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Block library templates should NOT extend other templates
        assert "{% extends" not in content, "Block library must not use {% extends %}"

    def test_template_has_metadata(self):
        """RED: Verify TEMPLATE_METADATA with ARCHITECTURAL enforcement."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must have TEMPLATE_METADATA
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

    def test_block_pattern_pytest_imports_exists(self):
        """RED: Verify pattern_pytest_imports block exists for pytest imports."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must define pattern_pytest_imports block
        assert "{% block pattern_pytest_imports %}" in content

    def test_block_pattern_pytest_fixtures_exists(self):
        """RED: Verify pattern_pytest_fixtures block exists for fixture definitions."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must define pattern_pytest_fixtures block
        assert "{% block pattern_pytest_fixtures %}" in content

    def test_block_pattern_pytest_marks_exists(self):
        """RED: Verify pattern_pytest_marks block exists for test decorators."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must define pattern_pytest_marks block
        assert "{% block pattern_pytest_marks %}" in content

    def test_block_pattern_pytest_parametrize_exists(self):
        """RED: Verify pattern_pytest_parametrize block exists for parametrized tests."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must define pattern_pytest_parametrize block
        assert "{% block pattern_pytest_parametrize %}" in content

    def test_import_from_concrete_template(self):
        """RED: Verify template blocks can be extended by a concrete template."""
        # Create a test concrete template that extends the pytest pattern
        test_template_content = """
{%- extends "tier3_pattern_python_pytest.jinja2" -%}

{# Test Concrete Template using blocks from pattern library #}

{# Override pattern_pytest_imports to add custom imports #}
{% block pattern_pytest_imports %}
{{ super() }}
from typing import Generator
{% endblock %}

{# Use pattern_pytest_fixtures without override (get default) #}

{# Override pattern_pytest_marks to add custom test #}
{% block pattern_pytest_marks %}
{{ super() }}

@pytest.mark.unit
def test_custom():
    assert True
{% endblock %}
        """

        # Try to render with Jinja2
        template_dir = Path("mcp_server/scaffolding/templates")
        env = Environment(loader=FileSystemLoader(template_dir))

        # Create template from string
        template = env.from_string(test_template_content)

        # Should render without errors
        result = template.render()

        # Verify result contains both base pattern and override
        assert result is not None
        assert "import pytest" in result  # From base pattern
        assert "from typing import Generator" in result  # From override
        assert "@pytest.mark.asyncio" in result  # From base pattern
        assert "@pytest.mark.unit" in result  # From override

    def test_pytest_imports_block_contains_pytest_import(self):
        """RED: Verify pattern_pytest_imports block includes pytest import."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Find the pattern_pytest_imports block content
        start = content.find("{% block pattern_pytest_imports %}")
        end = content.find("{% endblock %}", start)
        block_content = content[start:end]

        # Should contain pytest import
        assert "import pytest" in block_content

    def test_pytest_fixtures_block_contains_fixture_decorator(self):
        """RED: Verify pattern_pytest_fixtures block includes @pytest.fixture pattern."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Find the pattern_pytest_fixtures block content
        start = content.find("{% block pattern_pytest_fixtures %}")
        end = content.find("{% endblock %}", start)
        block_content = content[start:end]

        # Should contain @pytest.fixture decorator pattern
        assert "@pytest.fixture" in block_content

    def test_pytest_marks_block_contains_asyncio_marker(self):
        """RED: Verify pattern_pytest_marks block includes @pytest.mark.asyncio."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Find the pattern_pytest_marks block content
        start = content.find("{% block pattern_pytest_marks %}")
        end = content.find("{% endblock %}", start)
        block_content = content[start:end]

        # Should contain asyncio marker
        assert "@pytest.mark.asyncio" in block_content

    def test_pytest_parametrize_block_contains_decorator(self):
        """RED: Verify pattern_pytest_parametrize block includes @pytest.mark.parametrize."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Find the pattern_pytest_parametrize block content
        start = content.find("{% block pattern_pytest_parametrize %}")
        end = content.find("{% endblock %}", start)
        block_content = content[start:end]

        # Should contain parametrize decorator
        assert "@pytest.mark.parametrize" in block_content
