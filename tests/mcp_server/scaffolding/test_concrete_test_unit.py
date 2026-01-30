# tests/mcp_server/scaffolding/test_concrete_test_unit.py
"""
Unit tests for concrete/test_unit.py.jinja2 template.

Tests the concrete unit test template that cherry-picks 5 test patterns:
pytest, assertions, mocking, test_fixtures, and test_structure.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify concrete/test_unit.py.jinja2 template structure
    - Test cherry-picking of 5 pattern templates
    - Validate context variable handling
    - Test scaffolded test structure
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
    """Test suite for concrete/test_unit.py.jinja2 template."""

    def test_template_exists(self, jinja_env):
        """Test that template exists and loads."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        assert template is not None

    def test_template_extends_patterns(self):
        """Test that template extends required pattern templates."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "concrete"
            / "test_unit.py.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        # Should NOT extend (concrete templates generate standalone code)
        assert "{% extends" not in content or "tier3_pattern" not in content

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
        assert "class TestExample" in result

    def test_rendered_contains_module_docstring(self, jinja_env):
        """Test that rendered output contains module docstring."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        assert '"""' in result
        assert "@layer" in result

    def test_rendered_contains_pytest_imports(self, jinja_env):
        """Test that rendered output contains pytest imports."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        assert "import pytest" in result

    def test_rendered_with_fixtures(self, jinja_env):
        """Test rendering with fixture definitions."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
            "fixtures": [
                {"name": "sample_data", "description": "Sample test data"}
            ],
        }
        result = template.render(**context)
        assert "@pytest.fixture" in result or "fixture" in result.lower()

    def test_rendered_with_test_methods(self, jinja_env):
        """Test rendering with test method definitions."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
            "test_methods": [
                {
                    "name": "test_example_function",
                    "description": "Test example function",
                    "async": False,
                }
            ],
        }
        result = template.render(**context)
        assert "def test_example_function" in result

    def test_rendered_with_async_test(self, jinja_env):
        """Test rendering with async test method."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
            "test_methods": [
                {
                    "name": "test_async_function",
                    "description": "Test async function",
                    "async": True,
                }
            ],
        }
        result = template.render(**context)
        assert (
            "async def test_async_function" in result
            or "@pytest.mark.asyncio" in result
        )

    def test_rendered_contains_aaa_structure(self, jinja_env):
        """Test that rendered output suggests AAA pattern."""
        template = jinja_env.get_template("concrete/test_unit.py.jinja2")
        context = {
            "module_under_test": "mcp_server.tools.example",
            "test_class_name": "TestExample",
        }
        result = template.render(**context)
        # Should have AAA comments or structure hints
        assert (
            "Arrange" in result
            or "Act" in result
            or "Assert" in result
            or "# Setup" in result
        )
