# tests/mcp_server/scaffolding/test_tier3_pattern_python_translator.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:21Z updated=
"""Unit tests for tier3_pattern_python_translator.jinja2 template.

Tests the Tier 3 Translator/i18n pattern macro library.

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
        Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_dir)))


class TestTier3PatternPythonTranslator:
    """Tests for the tier3 Translator macro library template."""

    def test_template_exists(self, jinja_env):
        """Template exists and is loadable."""
        template = jinja_env.get_template("tier3_pattern_python_translator.jinja2")
        assert template is not None

    def test_template_has_no_extends_or_blocks(self):
        """Template is a macro library: no extends/blocks (outside comments)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_translator.jinja2"
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
            / "tier3_pattern_python_translator.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

        assert "{% macro pattern_translator_imports" in content

        # Backend-aligned usage (see backend/utils/translator.py)
        assert "{% macro pattern_translator_get" in content
        assert "{% macro pattern_translator_get_param_name" in content

        assert "{% macro pattern_translator_key_guideline" in content

    def test_macros_render_expected_tokens(self, jinja_env):
        """Rendered macros contain expected translator tokens."""
        template = jinja_env.get_template("tier3_pattern_python_translator.jinja2")

        imports_rendered = template.module.pattern_translator_imports()
        get_rendered = template.module.pattern_translator_get(
            key_expr="key",
            default_expr="key",
        )
        get_param_name_rendered = template.module.pattern_translator_get_param_name(
            param_path_expr="param_path",
            default_expr="param_path",
        )
        guideline_rendered = template.module.pattern_translator_key_guideline()

        assert "Translator" in imports_rendered

        assert "translator.get" in get_rendered
        assert "translator.get(key" in get_rendered
        assert "default=key" in get_rendered

        assert "translator.get_param_name" in get_param_name_rendered
        assert "translator.get_param_name(param_path" in get_param_name_rendered
        assert "default=param_path" in get_param_name_rendered

        assert "dot" in guideline_rendered
        assert "key" in guideline_rendered
