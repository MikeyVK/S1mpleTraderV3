# tests/mcp_server/scaffolding/test_tier3_pattern_python_assertions.py
"""
Unit tests for tier3_pattern_python_assertions template.

Tests the Tier 3 assertion pattern macro library for pytest-based testing.
Validates that template provides a minimal macro library (assertions are typically inline).

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify tier3_pattern_python_assertions.jinja2 template structure
    - Test macro library pattern (no {% extends %}, no blocks)
    - Validate TEMPLATE_METADATA presence and ARCHITECTURAL enforcement
    - Confirm minimal implementation (assertions are inline in tests)
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
        Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates"
    )
    return Environment(loader=FileSystemLoader(str(templates_dir)))


class TestTier3PatternPythonAssertions:
    """Test suite for tier3_pattern_python_assertions macro library."""

    def test_template_exists(self, jinja_env):
        """Test that template exists and loads."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        assert template is not None

    def test_template_has_no_extends(self):
        """Test that template follows macro library pattern (no extends, no blocks)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% extends" not in content

        # Check for blocks in non-comment code
        no_comments = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)
        assert "{% block" not in no_comments

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "provides_macros: []" in content

    def test_template_is_minimal(self):
        """Test that template is minimal (no macros for assertions)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        # Assertions pattern has no macros - assertions are written inline
        # Remove comments to check actual template code
        no_comments = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)
        assert "{% macro" not in no_comments

    def test_import_from_concrete_template(self, jinja_env):
        """Test that template can be imported (even though it provides no macros)."""
        # Template can be imported but provides no macros
        template_str = """
{% import "tier3_pattern_python_assertions.jinja2" as assertions_p %}
# No macros to call - assertions are inline
"""
        template = jinja_env.from_string(template_str)
        result = template.render()
        assert result is not None
        assert "# No macros to call" in result

    def test_template_renders_empty(self, jinja_env):
        """Test that template renders to minimal output (no code generation)."""
        template = jinja_env.get_template("tier3_pattern_python_assertions.jinja2")
        result = template.render()
        # Should be minimal/empty since no macros are defined
        assert result.strip() == ""

    def test_template_has_changelog(self):
        """Test that template documents refactor from blocks to macros."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "changelog" in content
        assert "2.0.0" in content
        assert "Refactor from" in content

    def test_template_explains_no_macros_needed(self):
        """Test that template explains why no macros are provided."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_assertions.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "inline" in content.lower() or "typically" in content.lower()
