# tests/mcp_server/scaffolding/test_tier3_pattern_python_error.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:15Z updated=
"""Unit tests for tier3_pattern_python_error.jinja2 template.

Tests the Tier 3 error-handling pattern macro library.

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib]
@responsibilities:
    - Verify template exists and loads
    - Enforce macro library constraints (no extends, no blocks)
    - Validate TEMPLATE_METADATA and required macros
    - Validate macros render expected tokens
"""

# Standard library
import re
from pathlib import Path

# Third-party
import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def jinja_env():
    """Jinja2 environment rooted at the scaffolding templates directory."""
    templates_dir = (
        Path(__file__).parent.parent.parent.parent
        / "mcp_server"
        / "scaffolding"
        / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_dir)))


class TestTier3PatternPythonError:
    """Tests for the tier3 error-handling macro library template."""

    def test_template_exists(self, jinja_env):
        """Template exists and is loadable."""
        template = jinja_env.get_template("tier3_pattern_python_error.jinja2")
        assert template is not None

    def test_template_has_no_extends_or_blocks(self):
        """Template is a macro library: no extends/blocks (outside comments)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_error.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "{% extends" not in content

        no_comments = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)
        assert "{% block" not in no_comments

    def test_template_has_metadata_and_macros(self):
        """Template includes metadata and required macro definitions."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_error.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

        assert "{% macro pattern_error_imports" in content
        assert "{% macro pattern_error_raise" in content
        assert "{% macro pattern_error_wrap" in content

    def test_macros_render_expected_tokens(self, jinja_env):
        """Rendered macros contain expected tokens."""
        template = jinja_env.get_template("tier3_pattern_python_error.jinja2")

        imports_rendered = getattr(template.module, "pattern_error_imports")()
        raise_rendered = getattr(template.module, "pattern_error_raise")(
            exc_class="WorkerInitializationError",
            worker_name_attr="_name",
            message="initialization failed",
        )
        wrap_rendered = getattr(template.module, "pattern_error_wrap")(
            exc_class="WorkerInitializationError",
            worker_name_attr="_name",
            message="initialization failed",
        )

        assert "WorkerInitializationError" in imports_rendered

        assert "raise" in raise_rendered
        assert "f\"{self._name}: initialization failed\"" in raise_rendered

        assert "try" in wrap_rendered
        assert "except Exception" in wrap_rendered
        assert "from exc" in wrap_rendered
        assert "f\"{self._name}: initialization failed\"" in wrap_rendered
