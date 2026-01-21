# artifact: type=unit_test, version=1.0, created=2026-01-21T21:31:54Z
# pylint: disable=redefined-outer-name  # pytest fixtures
"""
Unit tests for TemplateIntrospector.

Tests template AST parsing and schema extraction for validation
Following TDD: These tests are written BEFORE implementation (RED phase).
@layer: Tests (Unit)
@dependencies: [pytest, jinja2.Environment, jinja2.meta, mcp_server.scaffolding.template_introspector]
@responsibilities:
    - Test TemplateSchema dataclass structure and defaults
    - Test introspect_template() with various Jinja2 patterns
    - Test system field filtering (template_id, template_version, etc.)
    - Test variable classification (required vs optional)
    - Test error handling for invalid templates
    - Test sorting of schema fields
"""
# pyright: basic, reportPrivateUsage=false
# Standard library
from pathlib import Path
from typing import Any
from unittest.mock import Mock, MagicMock

# Third-party
import pytest
import jinja2

# Project modules
from mcp_server.scaffolding.template_introspector import (
    TemplateIntrospector,
)
from mcp_server.core.exceptions import (
    ExecutionError,
    ValidationError,
)
from mcp_server.scaffolding.template_introspector import TemplateSchema

@pytest.fixture(name="jinja2_env")
def fixture_jinja2_env() -> jinja2.Environment:
    """Provides configured Jinja2 environment for template parsing"""
    import jinja2
    return jinja2.Environment()

@pytest.fixture(name="sample_dto_template")
def fixture_sample_dto_template() -> str:
    """Provides sample DTO template with required and optional fields"""
    return '''
    class {{ name }}(BaseModel):
        """{{ description }}"""
        id: int
        {% if include_timestamps %}created_at: datetime{% endif %}
    '''

@pytest.fixture(name="system_fields")
def fixture_system_fields() -> set[str]:
    """Provides set of system-injected field names"""
    return {"template_id", "template_version", "scaffold_created", "output_path"}


class TestTemplateIntrospector:
    """Tests for TemplateIntrospector."""

    def test_introspect_extracts_required_variables(
        self,
        jinja2_env: jinja2.Environment,
        sample_dto_template: str
    ) -> None:
        """RED: introspect_template() identifies required variables (no defaults)"""
        # Arrange
        from mcp_server.scaffolding.template_introspector import introspect_template

        # Act
        schema = introspect_template(jinja2_env, sample_dto_template)

        # Assert
        assert "name" in schema.required
        assert "description" in schema.required
        assert len(schema.required) == 2

    def test_introspect_extracts_optional_variables(
        self,
        jinja2_env: jinja2.Environment,
        sample_dto_template: str
    ) -> None:
        """RED: introspect_template() identifies optional variables (with defaults)"""
        # Arrange
        from mcp_server.scaffolding.template_introspector import introspect_template

        # Act
        schema = introspect_template(jinja2_env, sample_dto_template)

        # Assert
        assert "include_timestamps" in schema.optional
        assert len(schema.optional) == 1

    def test_introspect_filters_system_fields(
        self,
        jinja2_env: jinja2.Environment,
        system_fields: set[str]
    ) -> None:
        """RED: introspect_template() excludes system-injected fields from schema"""
        # Arrange
        from mcp_server.scaffolding.template_introspector import introspect_template
        template_with_system_fields = '''
        # artifact: type={{ template_id }}, version={{ template_version }}, created={{ scaffold_created }}
        class {{ name }}:
            path = "{{ output_path }}"
        '''

        # Act
        schema = introspect_template(jinja2_env, template_with_system_fields)

        # Assert - system fields should NOT appear in schema
        for sys_field in system_fields:
            assert sys_field not in schema.required
            assert sys_field not in schema.optional
        # Only 'name' should be required (user-provided)
        assert "name" in schema.required

    def test_introspect_sorts_fields_alphabetically(
        self,
        jinja2_env: jinja2.Environment
    ) -> None:
        """RED: introspect_template() returns fields in sorted order"""
        # Arrange
        from mcp_server.scaffolding.template_introspector import introspect_template
        template = '''
        {{ zebra }}
        {{ alpha }}
        {{ middle }}
        {% if optional_z %}{% endif %}
        {% if optional_a %}{% endif %}
        '''

        # Act
        schema = introspect_template(jinja2_env, template)

        # Assert - fields should be alphabetically sorted
        assert schema.required == ["alpha", "middle", "zebra"]
        assert schema.optional == ["optional_a", "optional_z"]

    def test_introspect_handles_invalid_template_syntax(
        self,
        jinja2_env: jinja2.Environment
    ) -> None:
        """RED: introspect_template() raises ExecutionError for invalid Jinja2 syntax"""
        # Arrange
        from mcp_server.scaffolding.template_introspector import introspect_template
        invalid_template = '''
        {{ unclosed_variable
        {% if broken %}
        '''

        # Act & Assert
        with pytest.raises(ExecutionError) as exc_info:
            introspect_template(jinja2_env, invalid_template)

        # Verify error message mentions syntax/template issue
        error_msg = str(exc_info.value)
        assert "template" in error_msg.lower() or "syntax" in error_msg.lower()
