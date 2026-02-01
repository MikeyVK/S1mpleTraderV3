# tests/mcp_server/scaffolding/test_tier3_pattern_python_lifecycle.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:02Z updated=
"""Unit tests for tier3_pattern_python_lifecycle.jinja2 template.

Tests the Tier 3 lifecycle pattern macro library for IWorkerLifecycle.
Validates macro library rules (no {% extends %}, no {% block %}) and ensures
required macros exist and render expected method signatures.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib]
@responsibilities:
    - Verify template exists and loads
    - Enforce macro library constraints (no extends, no blocks)
    - Validate TEMPLATE_METADATA and ARCHITECTURAL enforcement
    - Validate required lifecycle macros render expected signatures
"""

# Standard library
import re
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


class TestTier3PatternPythonLifecycle:
    """Test suite for tier3_pattern_python_lifecycle macro library."""

    def test_template_exists(self, jinja_env):
        """Verify tier3_pattern_python_lifecycle.jinja2 exists and loads."""
        template = jinja_env.get_template("tier3_pattern_python_lifecycle.jinja2")
        assert template is not None

    def test_template_has_no_extends_or_blocks(self):
        """Verify template is a MACRO LIBRARY (no extends, no blocks)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_lifecycle.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "{% extends" not in content

        no_comments = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)
        assert "{% block" not in no_comments

    def test_template_has_metadata(self):
        """Verify TEMPLATE_METADATA with ARCHITECTURAL enforcement."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_lifecycle.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

    def test_required_macros_exist(self):
        """Verify lifecycle macros are defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_lifecycle.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "{% macro pattern_lifecycle_imports" in content
        assert "{% macro pattern_lifecycle_base_class" in content
        assert "{% macro pattern_lifecycle_init" in content
        assert "{% macro pattern_lifecycle_initialize" in content
        assert "{% macro pattern_lifecycle_shutdown" in content

    def test_macros_render_expected_signatures(self, jinja_env):
        """Verify lifecycle macros render imports + method signatures."""
        template = jinja_env.get_template("tier3_pattern_python_lifecycle.jinja2")

        imports_rendered = template.module.pattern_lifecycle_imports()
        initialize_rendered = template.module.pattern_lifecycle_initialize()
        shutdown_rendered = template.module.pattern_lifecycle_shutdown()

        assert "IWorkerLifecycle" in imports_rendered
        assert "WorkerInitializationError" in imports_rendered

        assert "def initialize" in initialize_rendered
        assert "strategy_cache" in initialize_rendered
        assert "**capabilities" in initialize_rendered

        assert "def shutdown" in shutdown_rendered
        assert "-> None" in shutdown_rendered
