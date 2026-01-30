"""
Unit tests for concrete/test_integration.py.jinja2 template.

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
        Path(__file__).parent.parent.parent.parent
        / "mcp_server"
        / "scaffolding"
        / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_path)))


class TestConcreteTestIntegration:
    """Test suite for concrete/test_integration.py.jinja2 template."""

    def test_template_exists(self, jinja_env):
        """Test that template file exists and can be loaded."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
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
            / "test_integration.py.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        # Concrete templates extend tier2 base (not tier3 patterns)
        assert '{% extends "tier2_base_python.jinja2" %}' in content
        assert "tier3_pattern" not in content.split("extends")[0]  # Not in extends statement

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "concrete"
            / "test_integration.py.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: GUIDELINE" in content

    def test_template_renders_with_minimal_context(self, jinja_env):
        """Test template renders with minimal required context."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
        }
        result = template.render(**context)
        assert result is not None
        assert len(result) > 100

    def test_rendered_contains_test_class(self, jinja_env):
        """Test that rendered output contains test class."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
        }
        result = template.render(**context)
        assert "class TestScaffoldingIntegration:" in result

    def test_rendered_contains_module_docstring(self, jinja_env):
        """Test that rendered output contains module-level docstring."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
        }
        result = template.render(**context)
        assert '"""' in result
        assert "@layer: Tests (Integration)" in result
        assert "@dependencies:" in result

    def test_rendered_contains_pytest_imports(self, jinja_env):
        """Test that rendered output contains pytest imports."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
        }
        result = template.render(**context)
        assert "import pytest" in result

    def test_rendered_with_workspace_fixture(self, jinja_env):
        """Test rendering with workspace fixture enabled."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
            "workspace_fixture": True,
        }
        result = template.render(**context)
        assert "@pytest.fixture" in result
        assert "temp_workspace" in result or "workspace" in result

    def test_rendered_with_managers(self, jinja_env):
        """Test rendering with manager setup."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
            "managers_needed": ["ArtifactManager", "TemplateManager"],
        }
        result = template.render(**context)
        assert "ArtifactManager" in result
        assert "TemplateManager" in result

    def test_rendered_with_async_test(self, jinja_env):
        """Test rendering with async test methods."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
            "test_methods": [
                {"name": "test_async_integration", "async": True, "fixtures": []},
            ],
        }
        result = template.render(**context)
        assert "async def test_async_integration" in result
        assert "@pytest.mark.asyncio" in result

    def test_rendered_contains_scenario_structure(self, jinja_env):
        """Test that rendered output contains scenario-based structure."""
        template = jinja_env.get_template("concrete/test_integration.py.jinja2")
        context = {
            "test_scenario": "artifact scaffolding E2E",
            "test_class_name": "TestScaffoldingIntegration",
        }
        result = template.render(**context)
        # Check for scenario-based documentation
        assert "artifact scaffolding E2E" in result or "Scenario:" in result
