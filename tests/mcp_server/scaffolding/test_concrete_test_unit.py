"""
Unit tests for concrete/test_unit.py.jinja2 template.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
"""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment with test templates path."""
    templates_path = (
        Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_path)))


class TestConcreteTestUnit:
    """Test suite for concrete/test_unit.py.jinja2 template."""

    def test_template_exists(self, jinja_env):
        """Test that template file exists and can be loaded."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        assert template is not None
        assert template.filename is not None

    def test_template_extends_tier2_base(self):
        """Test that template extends tier2_base_python."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "concrete"
            / "test_unit.py.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        # Concrete templates extend tier2 base (not tier3 patterns)
        assert '{% extends "tier2_base_python.jinja2" %}' in content
        assert "tier3_pattern" not in content.split("extends")[0]  # Not in extends statement

    def test_template_imports_tier3_patterns(self):
        """Test that template imports tier3 pattern templates."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "concrete"
            / "test_unit.py.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        # Template should import tier3 patterns for DRY composition
        assert '{% import "tier3_pattern_python_' in content
        assert "pytest" in content or "test_fixtures" in content

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "concrete"
            / "test_unit.py.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: GUIDELINE" in content

    def test_template_renders_with_minimal_context(self, jinja_env):
        """Test template renders with minimal required context."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        assert result is not None
        assert len(result) > 100

    def test_rendered_contains_test_class(self, jinja_env):
        """Test that rendered output contains test class."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        assert "class TestExample:" in result

    def test_rendered_contains_module_docstring(self, jinja_env):
        """Test that rendered output contains module-level docstring."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        assert '"""' in result
        assert "@layer: Tests (Unit)" in result
        assert "@dependencies:" in result

    def test_rendered_contains_pytest_imports(self, jinja_env):
        """Test that rendered output contains pytest imports."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        assert "import pytest" in result

    def test_rendered_with_test_methods(self, jinja_env):
        """Test rendering with test method definitions."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
            "test_methods": [
                {"name": "test_example_behavior", "async": False},
            ],
        }
        result = template.render(**context)
        assert "def test_example_behavior" in result

    def test_rendered_with_async_test(self, jinja_env):
        """Test rendering with async test methods."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
            "test_methods": [
                {"name": "test_async_behavior", "async": True},
            ],
        }
        result = template.render(**context)
        assert "async def test_async_behavior" in result
        assert "@pytest.mark.asyncio" in result

    def test_rendered_contains_aaa_structure(self, jinja_env):
        """Test that rendered output contains AAA (Arrange-Act-Assert) structure hints."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        # Check for AAA pattern hints
        assert "Arrange" in result or "# TODO: Set up test data" in result
        assert "Act" in result or "# TODO: Execute function under test" in result
        assert "Assert" in result or "assert" in result
