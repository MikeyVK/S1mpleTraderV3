# tests/mcp_server/scaffolding/test_concrete_test_unit.py
"""
Unit tests for concrete test_unit template.

Tests the concrete test_unit.py.jinja2 template that composes multiple
tier 3 test pattern templates via {% extends %} and cherry-picking blocks.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify concrete/test_unit.py.jinja2 template structure
    - Test composition of 5 tier3 patterns (pytest, assertions, mocking, fixtures, structure)
    - Validate TEMPLATE_METADATA and GUIDELINE enforcement
    - Test context variable rendering
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


class TestConcreteTestUnit:
    """Test suite for concrete test_unit template."""

    def test_template_exists(self, jinja_env):
        """Test that concrete test_unit template exists and loads."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        assert template is not None

    def test_template_extends_tier2(self):
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
        assert '{% extends "tier2_base_python.jinja2" %}' in content

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA with GUIDELINE."""
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
        """Test that template renders with minimal context."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.test_tool",
            "test_class_name": "TestTestTool",
            "fixtures": [],
            "test_methods": [],
        }
        result = template.render(**context)
        assert result is not None
        assert len(result) > 0

    def test_template_contains_pytest_imports(self, jinja_env):
        """Test that rendered template includes pytest imports."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [],
            "test_methods": [],
        }
        result = template.render(**context)
        assert "import pytest" in result

    def test_template_contains_test_class(self, jinja_env):
        """Test that rendered template includes test class."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [],
            "test_methods": [],
        }
        result = template.render(**context)
        assert "class TestModule" in result

    def test_template_renders_fixtures(self, jinja_env):
        """Test that template renders fixtures from context."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [
                {
                    "name": "sample_fixture",
                    "type": "simple",
                    "description": "Sample test fixture",
                }
            ],
            "test_methods": [],
        }
        result = template.render(**context)
        assert "@pytest.fixture" in result
        assert "sample_fixture" in result

    def test_template_renders_test_methods(self, jinja_env):
        """Test that template renders test methods from context."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [],
            "test_methods": [
                {
                    "name": "test_basic_functionality",
                    "description": "Test basic functionality",
                    "async": False,
                }
            ],
        }
        result = template.render(**context)
        assert "def test_basic_functionality" in result

    def test_template_renders_async_test_methods(self, jinja_env):
        """Test that template renders async test methods."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [],
            "test_methods": [
                {
                    "name": "test_async_operation",
                    "description": "Test async operation",
                    "async": True,
                }
            ],
        }
        result = template.render(**context)
        assert "async def test_async_operation" in result
        assert "@pytest.mark.asyncio" in result

    def test_template_contains_module_docstring(self, jinja_env):
        """Test that template contains comprehensive module docstring."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [],
            "test_methods": [],
        }
        result = template.render(**context)
        assert '"""' in result
        assert "@layer: Tests (Unit)" in result

    def test_template_uses_aaa_pattern(self, jinja_env):
        """Test that template demonstrates AAA pattern."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "test_module",
            "test_class_name": "TestModule",
            "fixtures": [],
            "test_methods": [
                {
                    "name": "test_example",
                    "description": "Test example",
                    "async": False,
                }
            ],
        }
        result = template.render(**context)
        # Should have AAA comments or structure
        assert "Arrange" in result or "Act" in result or "Assert" in result
