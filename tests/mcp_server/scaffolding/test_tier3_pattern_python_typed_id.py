# tests/mcp_server/scaffolding/test_tier3_pattern_python_typed_id.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:21Z updated=
"""Unit tests for tier3_pattern_python_typed_id.jinja2 template.

Tests the Tier 3 typed-id generation pattern macro library.

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


class TestTier3PatternPythonTypedId:
    """Tests for the tier3 typed-id macro library template."""

    def test_template_exists(self, jinja_env):
        """Template exists and is loadable."""
        template = jinja_env.get_template("tier3_pattern_python_typed_id.jinja2")
        assert template is not None

    def test_template_has_no_extends_or_blocks(self):
        """Template is a macro library: no extends/blocks (outside comments)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_typed_id.jinja2"
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
            / "tier3_pattern_python_typed_id.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

        assert "{% macro pattern_typed_id_imports" in content
        assert "{% macro pattern_typed_id_default_factory" in content
        assert "{% macro pattern_typed_id_generate" in content

    def test_macros_render_expected_tokens(self, jinja_env):
        """Rendered macros contain expected typed-id tokens."""
        template = jinja_env.get_template("tier3_pattern_python_typed_id.jinja2")

        imports_rendered = getattr(template.module, "pattern_typed_id_imports")(
            function_name="generate_trade_plan_id",
        )
        default_factory_rendered = getattr(
            template.module,
            "pattern_typed_id_default_factory",
        )(
            function_name="generate_trade_plan_id",
        )
        gen_rendered = getattr(template.module, "pattern_typed_id_generate")(
            function_name="generate_trade_plan_id",
        )

        assert "id_generators" in imports_rendered
        assert "generate_trade_plan_id" in imports_rendered

        assert "default_factory" in default_factory_rendered
        assert "default_factory=generate_trade_plan_id" in default_factory_rendered

        assert "generate_trade_plan_id()" in gen_rendered
