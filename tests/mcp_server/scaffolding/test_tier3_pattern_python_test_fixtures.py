# tests/mcp_server/scaffolding/test_tier3_pattern_python_test_fixtures.py
"""
Unit tests for tier3_pattern_python_test_fixtures template.

Tests the Tier 3 test fixtures pattern macro library for pytest.
Validates that template provides pattern_fixture_decorator() macro for generating
@pytest.fixture decorators with options (scope, autouse, params).

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify tier3_pattern_python_test_fixtures.jinja2 template structure
    - Test macro library pattern (no {% extends %}, no blocks)
    - Validate TEMPLATE_METADATA presence and ARCHITECTURAL enforcement
    - Test pattern_fixture_decorator() macro functionality with options
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


class TestTier3PatternPythonTestFixtures:
    """Test suite for tier3_pattern_python_test_fixtures macro library."""

    def test_template_exists(self, jinja_env):
        """Test that template exists and loads."""
        template = jinja_env.get_template(
            "tier3_pattern_python_test_fixtures.jinja2"
        )
        assert template is not None

    def test_template_has_no_extends(self):
        """Test that template follows macro library pattern (no extends, no blocks)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% extends" not in content
        
        # Check for blocks in non-comment code
        no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)
        assert "{% block" not in no_comments

    def test_template_has_metadata(self):
        """Test that template contains TEMPLATE_METADATA."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "provides_macros: [pattern_fixture_decorator]" in content

    def test_macro_pattern_fixture_decorator_exists(self):
        """Test that pattern_fixture_decorator macro is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% macro pattern_fixture_decorator(" in content

    def test_macro_generates_simple_fixture_decorator(self, jinja_env):
        """Test that macro generates simple @pytest.fixture decorator."""
        template_str = """
{% import "tier3_pattern_python_test_fixtures.jinja2" as fixtures_p %}
{{ fixtures_p.pattern_fixture_decorator("my_fixture") }}
def my_fixture():
    return "value"
"""
        template = jinja_env.from_string(template_str)
        result = template.render().strip()
        
        assert "@pytest.fixture" in result
        assert "def my_fixture():" in result

    def test_macro_generates_fixture_with_scope(self, jinja_env):
        """Test that macro generates fixture with scope parameter."""
        template_str = """
{% import "tier3_pattern_python_test_fixtures.jinja2" as fixtures_p %}
{{ fixtures_p.pattern_fixture_decorator("session_fixture", scope="session") }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render().strip()
        
        assert '@pytest.fixture(scope="session")' in result

    def test_macro_generates_fixture_with_autouse(self, jinja_env):
        """Test that macro generates fixture with autouse parameter."""
        template_str = """
{% import "tier3_pattern_python_test_fixtures.jinja2" as fixtures_p %}
{{ fixtures_p.pattern_fixture_decorator("auto_fixture", autouse=True) }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render().strip()
        
        assert "@pytest.fixture(autouse=True)" in result

    def test_macro_generates_fixture_with_params(self, jinja_env):
        """Test that macro generates fixture with params parameter."""
        template_str = """
{% import "tier3_pattern_python_test_fixtures.jinja2" as fixtures_p %}
{{ fixtures_p.pattern_fixture_decorator("param_fixture", params="[1, 2, 3]") }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render().strip()
        
        assert "@pytest.fixture(params=[1, 2, 3])" in result

    def test_macro_can_be_imported(self, jinja_env):
        """Test that template can be imported and macro is accessible."""
        template_str = """
{% import "tier3_pattern_python_test_fixtures.jinja2" as fixtures_p %}
{{ fixtures_p.pattern_fixture_decorator("test_fixture") | trim }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render()
        assert result is not None
        assert "@pytest.fixture" in result

    def test_template_has_changelog(self):
        """Test that template documents refactor from blocks to macros."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "changelog" in content
        assert "2.0.0" in content
        assert "Refactor from" in content

    def test_template_minimal_content(self):
        """Test that template has minimal content (1 macro, no example fixtures)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_test_fixtures.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        
        # Count macros in actual code (not comments)
        no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)
        macro_count = no_comments.count("{% macro")
        assert macro_count == 1
        
        # No example fixture implementations (old blocks had ~200 lines)
        assert "def sample_fixture():" not in content
        assert "yield" not in content.lower() or "yield" in "{#"  # Only in comments
