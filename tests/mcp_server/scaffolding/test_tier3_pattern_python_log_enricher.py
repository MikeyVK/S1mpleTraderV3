# tests/mcp_server/scaffolding/test_tier3_pattern_python_log_enricher.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:18Z updated=
"""Unit tests for tier3_pattern_python_log_enricher.jinja2 template.

Tests the Tier 3 LogEnricher pattern macro library.

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


class TestTier3PatternPythonLogEnricher:
    """Tests for the tier3 LogEnricher macro library template."""

    def test_template_exists(self, jinja_env):
        """Template exists and is loadable."""
        template = jinja_env.get_template("tier3_pattern_python_log_enricher.jinja2")
        assert template is not None

    def test_template_has_no_extends_or_blocks(self):
        """Template is a macro library: no extends/blocks (outside comments)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_log_enricher.jinja2"
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
            / "tier3_pattern_python_log_enricher.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

        # Core macros
        assert "{% macro pattern_log_enricher_imports" in content
        assert "{% macro pattern_log_enricher_set_logger" in content
        assert "{% macro pattern_log_enricher_child" in content

        # Backend-aligned convenience methods (see backend/utils/app_logger.py)
        assert "{% macro pattern_log_enricher_setup" in content
        assert "{% macro pattern_log_enricher_match" in content
        assert "{% macro pattern_log_enricher_filter" in content
        assert "{% macro pattern_log_enricher_policy" in content
        assert "{% macro pattern_log_enricher_result" in content
        assert "{% macro pattern_log_enricher_trade" in content

    def test_macros_render_expected_tokens(self, jinja_env):
        """Rendered macros contain expected LogEnricher usage tokens."""
        template = jinja_env.get_template("tier3_pattern_python_log_enricher.jinja2")

        imports_rendered = getattr(template.module, "pattern_log_enricher_imports")()
        set_rendered = getattr(template.module, "pattern_log_enricher_set_logger")(
            attr_name="logger",
        )
        child_rendered = getattr(template.module, "pattern_log_enricher_child")(
            indent_delta=1,
        )

        setup_rendered = getattr(template.module, "pattern_log_enricher_setup")(
            message_key="log.setup.example",
            values="worker_name=worker_name",
        )
        match_rendered = getattr(template.module, "pattern_log_enricher_match")(
            message_key="log.match.example",
            values="symbol=symbol",
        )
        filter_rendered = getattr(template.module, "pattern_log_enricher_filter")(
            message_key="log.filter.example",
            values="count=count",
        )
        policy_rendered = getattr(template.module, "pattern_log_enricher_policy")(
            message_key="log.policy.example",
            values="rule=rule",
        )
        result_rendered = getattr(template.module, "pattern_log_enricher_result")(
            message_key="log.result.example",
            values="ok=ok",
        )
        trade_rendered = getattr(template.module, "pattern_log_enricher_trade")(
            message_key="log.trade.example",
            values="trade_id=trade_id",
        )

        assert "LogEnricher" in imports_rendered
        assert "self.logger" in set_rendered

        # Child logger pattern: keep same underlying logger; bump indent
        assert "LogEnricher" in child_rendered
        assert "self.logger.logger" in child_rendered
        assert "self.logger.extra" in child_rendered
        assert "indent" in child_rendered

        # Backend convenience methods
        assert 'self.logger.setup("log.setup.example"' in setup_rendered
        assert "worker_name=worker_name" in setup_rendered

        assert 'self.logger.match("log.match.example"' in match_rendered
        assert "symbol=symbol" in match_rendered

        assert 'self.logger.filter("log.filter.example"' in filter_rendered
        assert "count=count" in filter_rendered

        assert 'self.logger.policy("log.policy.example"' in policy_rendered
        assert "rule=rule" in policy_rendered

        assert 'self.logger.result("log.result.example"' in result_rendered
        assert "ok=ok" in result_rendered

        assert 'self.logger.trade("log.trade.example"' in trade_rendered
        assert "trade_id=trade_id" in trade_rendered
