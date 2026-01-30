# tests/mcp_server/scaffolding/test_tier3_pattern_python_mocking.py
"""
Unit tests for tier3_pattern_python_mocking template.

Tests the Tier 3 mocking pattern macro library for pytest-based testing.
Validates that template provides pattern_mock_imports() macro for generating
unittest.mock imports (Mock, MagicMock, AsyncMock, patch).

@layer: Tests (Unit)
@dependencies: [pytest, jinja2, pathlib, mcp_server.scaffolding]
@responsibilities:
    - Verify tier3_pattern_python_mocking.jinja2 template structure
    - Test macro library pattern (no {% extends %}, no blocks)
    - Validate TEMPLATE_METADATA presence and ARCHITECTURAL enforcement
    - Test pattern_mock_imports() macro functionality
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


class TestTier3PatternPythonMocking:
    """Test suite for tier3_pattern_python_mocking macro library."""

    def test_template_exists(self, jinja_env):
        """Test that template exists and loads."""
        template = jinja_env.get_template(
            "tier3_pattern_python_mocking.jinja2"
        )
        assert template is not None

    def test_template_has_no_extends(self):
        """Test that template follows macro library pattern (no extends, no blocks)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_mocking.jinja2"
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
            / "tier3_pattern_python_mocking.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "provides_macros: [pattern_mock_imports]" in content

    def test_macro_pattern_mock_imports_exists(self):
        """Test that pattern_mock_imports macro is defined."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_mocking.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "{% macro pattern_mock_imports()" in content

    def test_macro_generates_mock_imports(self, jinja_env):
        """Test that pattern_mock_imports macro generates correct imports."""
        template_str = """
{% import "tier3_pattern_python_mocking.jinja2" as mocking_p %}
{{ mocking_p.pattern_mock_imports() }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render().strip()
        
        # Check for all expected imports
        assert "from unittest.mock import" in result
        assert "Mock" in result
        assert "MagicMock" in result
        assert "AsyncMock" in result
        assert "patch" in result

    def test_macro_can_be_imported(self, jinja_env):
        """Test that template can be imported and macro is accessible."""
        template_str = """
{% import "tier3_pattern_python_mocking.jinja2" as mocking_p %}
{# Macro exists and can be called #}
{{ mocking_p.pattern_mock_imports() | trim }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render()
        assert result is not None
        assert "unittest.mock" in result

    def test_template_has_changelog(self):
        """Test that template documents refactor from blocks to macros."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_mocking.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        assert "changelog" in content
        assert "2.0.0" in content
        assert "Refactor from" in content

    def test_macro_output_is_valid_python(self, jinja_env):
        """Test that macro generates valid Python import statement."""
        template_str = """
{% import "tier3_pattern_python_mocking.jinja2" as mocking_p %}
{{ mocking_p.pattern_mock_imports() | trim }}
"""
        template = jinja_env.from_string(template_str)
        result = template.render().strip()
        
        # Valid Python import: starts with 'from', contains 'import', has comma-separated names
        assert result.startswith("from unittest.mock import")
        assert "," in result  # Multiple imports comma-separated

    def test_template_minimal_content(self):
        """Test that template has minimal content (1 macro, no example code)."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_mocking.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")
        
        # Count macros in actual code (not comments)
        no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)
        macro_count = no_comments.count("{% macro")
        assert macro_count == 1
        
        # No example mocking code (old blocks had ~150 lines of examples)
        assert "mock_obj = Mock()" not in content
        assert "@patch(" not in content.lower() or "@patch(" in "{% macro" # Only in macro name
