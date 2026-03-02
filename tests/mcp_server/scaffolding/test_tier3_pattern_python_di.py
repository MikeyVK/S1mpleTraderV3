# tests/mcp_server/scaffolding/test_tier3_pattern_python_di.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:24Z updated=
"""Unit tests for tier3_pattern_python_di.jinja2 template.

Tests the Tier 3 DI-via-capabilities pattern macro library.

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


class TestTier3PatternPythonDi:
    """Tests for the tier3 DI macro library template."""

    def test_template_exists(self, jinja_env):
        """Template exists and is loadable."""
        template = jinja_env.get_template("tier3_pattern_python_di.jinja2")
        assert template is not None

    def test_template_has_no_extends_or_blocks(self):
        """Template is a macro library: no extends/blocks (outside comments)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_di.jinja2"
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
            / "tier3_pattern_python_di.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

        assert "{% macro pattern_di_imports" in content

        # Backend-aligned initialize() guard clauses (see backend/core/flow_initiator.py)
        assert "{% macro pattern_di_require_dependency" in content
        assert "{% macro pattern_di_require_capability" in content

        assert "{% macro pattern_di_set_dependency" in content
        assert "{% macro pattern_di_set_capability" in content

    def test_macros_render_expected_tokens(self, jinja_env):
        """Rendered macros contain expected DI tokens."""
        template = jinja_env.get_template("tier3_pattern_python_di.jinja2")

        imports_rendered = template.module.pattern_di_imports()

        require_dep_rendered = template.module.pattern_di_require_dependency(
            dep_name="strategy_cache",
            worker_name_attr="_name",
            details="required for Platform-within-Strategy worker",
        )
        require_cap_rendered = template.module.pattern_di_require_capability(
            cap_key="dto_types",
            worker_name_attr="_name",
            details="capability required for DTO type resolution",
        )

        set_dep_rendered = template.module.pattern_di_set_dependency(
            attr_name="_cache",
            dep_name="strategy_cache",
        )
        set_cap_rendered = template.module.pattern_di_set_capability(
            attr_name="_dto_types",
            cap_key="dto_types",
        )

        assert "WorkerInitializationError" in imports_rendered

        assert "if strategy_cache is None" in require_dep_rendered
        assert "raise WorkerInitializationError" in require_dep_rendered
        assert "di.dependency.strategy_cache" in require_dep_rendered

        assert 'if "dto_types" not in capabilities' in require_cap_rendered
        assert "raise WorkerInitializationError" in require_cap_rendered
        assert "di.capability.dto_types" in require_cap_rendered
        assert "self._cache" in set_dep_rendered
        assert "= strategy_cache" in set_dep_rendered

        assert "self._dto_types" in set_cap_rendered
        assert 'capabilities["dto_types"]' in set_cap_rendered
