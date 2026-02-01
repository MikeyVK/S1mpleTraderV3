# tests/mcp_server/scaffolding/test_tier3_pattern_python_pydantic.py
# template=unit_test version=6b0f1f7e created=2026-02-01T14:09Z updated=
"""
Unit tests for mcp_server.scaffolding.renderer.

Tests the tier3_pattern_python_pydantic.jinja2 macro library (Tier 3 pattern).

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.scaffolding.renderer]
@responsibilities:
    - Test TestTier3PatternPythonPydantic functionality
    - Verify template structure and required pydantic macros
    - Enforce macro library constraints and metadata compliance
"""

# Standard library
from typing import Any

# Third-party
import pytest
from pathlib import Path

# Project modules
from mcp_server.scaffolding.renderer import JinjaRenderer


class TestTier3PatternPythonPydantic:
    """Test suite for renderer."""

    def test_template_exists(
        self    ):
        """Verify tier3_pattern_python_pydantic.jinja2 exists and loads.."""
        # Arrange - Setup test data and preconditions
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        templates_dir = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(templates_dir)))

        # Act - Execute the functionality being tested
        template = env.get_template("tier3_pattern_python_pydantic.jinja2")

        # Assert - Verify the expected outcome
        assert template is not None
    def test_template_has_no_extends_or_blocks(
        self    ):
        """Verify macro library rule: no extends and no blocks (outside comments).."""
        # Arrange - Setup test data and preconditions
        import re
        from pathlib import Path

        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_pydantic.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        # Act - Execute the functionality being tested
        no_comments = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)

        # Assert - Verify the expected outcome
        assert "{% extends" not in content
        assert "{% block" not in no_comments
    def test_template_has_metadata_and_macros(
        self    ):
        """Verify TEMPLATE_METADATA and required macros exist.."""
        # Arrange - Setup test data and preconditions
        from pathlib import Path

        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
            / "tier3_pattern_python_pydantic.jinja2"
        )
        content = template_path.read_text(encoding="utf-8")

        # Act - Execute the functionality being tested
        # metadata and macro existence checks

        # Assert - Verify the expected outcome
        assert "TEMPLATE_METADATA" in content
        assert "enforcement: ARCHITECTURAL" in content
        assert "tier: 3" in content
        assert "category: pattern" in content

        assert "{% macro pattern_pydantic_imports" in content
        assert "{% macro pattern_pydantic_base_model" in content
        assert "{% macro pattern_pydantic_config" in content
        assert "{% macro pattern_pydantic_field" in content
        assert "{% macro pattern_pydantic_validator" in content
    def test_macros_render_expected_tokens(
        self    ):
        """Verify macros render expected pydantic tokens.."""
        # Arrange - Setup test data and preconditions
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path

        templates_dir = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("tier3_pattern_python_pydantic.jinja2")

        # Act - Execute the functionality being tested
        imports_rendered = template.module.pattern_pydantic_imports()
        base_rendered = template.module.pattern_pydantic_base_model()
        field_rendered = template.module.pattern_pydantic_field(name="foo", type_="str", description_key="dto.foo")
        validator_rendered = template.module.pattern_pydantic_validator(field_name="foo")

        # Assert - Verify the expected outcome
        assert "from pydantic" in imports_rendered
        assert "BaseModel" in imports_rendered

        assert "class" in base_rendered
        assert "(BaseModel" in base_rendered

        assert "Field(" in field_rendered
        assert "dto.foo" in field_rendered

        assert "@field_validator" in validator_rendered
