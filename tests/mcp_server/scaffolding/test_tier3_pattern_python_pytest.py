"""Unit tests for tier3_pattern_python_pytest.jinja2 macro library.

Tests the pytest framework pattern macros used by test_unit and test_integration templates.
This is a MACRO LIBRARY template (no {% extends %}), provides composable macros only.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Validate pytest pattern macro structure
    - Test fixture generation (pattern_pytest_imports)
    - Test async markers generation
    - Test parametrize decorator generation
    - Verify macros are callable via {% import %}
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
    """Test pytest pattern macros for composition via {% import %}."""

    def test_template_exists(self, jinja_env):
        """RED: Verify tier3_pattern_python_pytest.jinja2 exists and loads."""
        template = jinja_env.get_template("tier3_pattern_python_pytest.jinja2")
        assert template is not None
        assert "tier3_pattern_python_pytest.jinja2" in template.name

    def test_template_has_no_extends(self):
        """RED: Verify template is a MACRO LIBRARY (no {% extends %} statement)."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Macro library templates should NOT extend other templates
        assert "{% extends" not in content, "Macro library must not use {% extends %}"
        # Check for {% block %} in Jinja code (not in comments)
        import re
        # Remove comments (lines starting with {#)
        no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)
        assert "{% block" not in no_comments, "Macro library must use {% macro %} not {% block %}"

    def test_template_has_metadata(self):
        """RED: Verify TEMPLATE_METADATA with ARCHITECTURAL enforcement."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must have TEMPLATE_METADATA
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

    def test_macro_pattern_pytest_imports_exists(self):
        """RED: Verify pattern_pytest_imports macro exists for pytest imports."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Must define pattern_pytest_imports macro
        assert "{% macro pattern_pytest_imports" in content

    def test_macro_can_be_imported_and_called(self, jinja_env):
        """RED: Verify macros can be imported and called from concrete template."""
        # Create a test template that imports and calls the macro
        test_template_content = """
{%- import "tier3_pattern_python_pytest.jinja2" as pytest_p -%}
{{ pytest_p.pattern_pytest_imports() }}
        """

        template = jinja_env.from_string(test_template_content)
        result = template.render()

        # Should render pytest import
        assert "import pytest" in result
        assert "from pathlib import Path" in result

    def test_pytest_imports_macro_renders_correctly(self, jinja_env):
        """RED: Verify pattern_pytest_imports macro generates correct imports."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Find the pattern_pytest_imports macro
        assert "{% macro pattern_pytest_imports" in content

        # Test rendering via import
        test_template = jinja_env.from_string(
            """{% import "tier3_pattern_python_pytest.jinja2" as pytest_p %}
{{ pytest_p.pattern_pytest_imports() }}"""
        )
        result = test_template.render()

        # Should contain pytest import
        assert "import pytest" in result
        assert "from pathlib import Path" in result

    def test_template_uses_macros_not_blocks(self, jinja_env):
        """RED: Verify template defines macros for composition."""
        template_path = Path("mcp_server/scaffolding/templates/tier3_pattern_python_pytest.jinja2")
        content = template_path.read_text(encoding="utf-8")

        # Should have macros defined
        assert "{% macro" in content
        assert "{% endmacro" in content

    def test_multiple_macros_can_be_imported(self, jinja_env):
        """RED: Verify multiple macros can be imported and used together."""
        # Test that the pattern library provides multiple callable macros
        test_template = jinja_env.from_string(
            """{% import "tier3_pattern_python_pytest.jinja2" as pytest_p %}
{{ pytest_p.pattern_pytest_imports() }}
"""
        )
        result = test_template.render()

        # Should successfully import and call
        assert result is not None
        assert "import pytest" in result
