"""Unit tests for tier3_pattern_python_lifecycle.jinja2 macro library.

Validates the Tier 3 lifecycle pattern template for IWorkerLifecycle.
This is a MACRO LIBRARY template (no {% extends %}), provides composable macros only.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, re]
@responsibilities:
    - Verify tier3_pattern_python_lifecycle.jinja2 exists and loads
    - Enforce macro-library rules (no extends, no blocks)
    - Validate TEMPLATE_METADATA presence and ARCHITECTURAL enforcement
    - Validate required lifecycle macros exist and render expected content
"""

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env() -> Environment:
    """Create Jinja2 environment with template loader."""
    templates_dir = (
        Path(__file__).parent.parent.parent.parent
        / "mcp_server"
        / "scaffolding"
        / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_dir)))


class TestTier3PatternPythonLifecycle:
    """Test suite for tier3_pattern_python_lifecycle macro library."""

    def test_template_exists(self, jinja_env: Environment) -> None:
        """RED: Verify tier3_pattern_python_lifecycle.jinja2 exists and loads."""
        template = jinja_env.get_template("tier3_pattern_python_lifecycle.jinja2")
        assert template is not None
        assert "tier3_pattern_python_lifecycle.jinja2" in template.name

    def test_template_has_no_extends_or_blocks(self) -> None:
        """RED: Verify template is a MACRO LIBRARY (no extends, no blocks)."""
        template_path = Path(
            "mcp_server/scaffolding/templates/tier3_pattern_python_lifecycle.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "{% extends" not in content

        no_comments = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)
        assert "{% block" not in no_comments

    def test_template_has_metadata(self) -> None:
        """RED: Verify TEMPLATE_METADATA with ARCHITECTURAL enforcement."""
        template_path = Path(
            "mcp_server/scaffolding/templates/tier3_pattern_python_lifecycle.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

    def test_required_macros_exist(self) -> None:
        """RED: Verify lifecycle macros are defined."""
        template_path = Path(
            "mcp_server/scaffolding/templates/tier3_pattern_python_lifecycle.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "{% macro pattern_lifecycle_imports" in content
        assert "{% macro pattern_lifecycle_base_class" in content
        assert "{% macro pattern_lifecycle_init" in content
        assert "{% macro pattern_lifecycle_initialize" in content
        assert "{% macro pattern_lifecycle_shutdown" in content

    def test_imports_macro_renders_expected_imports(self, jinja_env: Environment) -> None:
        """RED: Verify pattern_lifecycle_imports renders expected imports."""
        template = jinja_env.get_template("tier3_pattern_python_lifecycle.jinja2")
        rendered = template.module.pattern_lifecycle_imports()
        assert "IWorkerLifecycle" in rendered
        assert "WorkerInitializationError" in rendered

    def test_initialize_macro_renders_signature(self, jinja_env: Environment) -> None:
        """RED: Verify initialize macro matches protocol signature."""
        template = jinja_env.get_template("tier3_pattern_python_lifecycle.jinja2")
        rendered = template.module.pattern_lifecycle_initialize()
        assert "def initialize" in rendered
        assert "strategy_cache" in rendered
        assert "**capabilities" in rendered

    def test_shutdown_macro_renders_signature(self, jinja_env: Environment) -> None:
        """RED: Verify shutdown macro matches protocol signature."""
        template = jinja_env.get_template("tier3_pattern_python_lifecycle.jinja2")
        rendered = template.module.pattern_lifecycle_shutdown()
        assert "def shutdown" in rendered
        assert "-> None" in rendered
