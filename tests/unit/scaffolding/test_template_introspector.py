# artifact: type=unit_test, version=1.0, created=2026-01-21T21:31:54Z
"""
Unit tests for TemplateIntrospector.

Tests template AST parsing and schema extraction for validation
Following TDD: These tests are written BEFORE implementation (RED phase).
@layer: Tests (Unit)
@dependencies: [pytest, jinja2.Environment, jinja2.meta,
                mcp_server.scaffolding.template_introspector]
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

# Third-party
import jinja2
import pytest

# Project modules
from mcp_server.core.exceptions import ExecutionError
from mcp_server.scaffolding.template_introspector import (
    introspect_template,
    introspect_template_with_inheritance,
)


@pytest.fixture(name="jinja2_env")
def fixture_jinja2_env() -> jinja2.Environment:
    """Provides configured Jinja2 environment for template parsing"""
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
        # (sample_dto_template fixture provides template)

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
        # (sample_dto_template fixture provides template)

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
        template_with_system_fields = """
        # artifact: type={{ template_id }}, version={{ template_version }}
        # created={{ scaffold_created }}
        class {{ name }}:
            path = "{{ output_path }}"
        """

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
        template = """
        {{ zebra }}
        {{ alpha }}
        {{ middle }}
        {% if optional_z %}{% endif %}
        {% if optional_a %}{% endif %}
        """

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
        invalid_template = """
        {{ unclosed_variable
        {% if broken %}
        """

        # Act & Assert
        with pytest.raises(ExecutionError) as exc_info:
            introspect_template(jinja2_env, invalid_template)

        # Verify error message mentions syntax/template issue
        error_msg = str(exc_info.value)
        assert "template" in error_msg.lower() or "syntax" in error_msg.lower()


class TestTemplateIntrospectorInheritance:
    """Tests for template introspection with inheritance chain support (Task 2.1)."""

    def test_introspect_worker_template_detects_parent_variables(self) -> None:
        """RED: introspect_template_with_inheritance() detects parent vars.

        Worker template inheritance chain:
        - worker.py.jinja2 (concrete): name, worker_scope, capabilities,
          module_description, responsibilities
        - tier2_base_python.jinja2: class_name (but worker overrides blocks)
        - tier1_base_code.jinja2: layer, dependencies, responsibilities,
          module_title, module_description, class_name
        - tier0_base_artifact.jinja2: template_id, template_version,
          scaffold_created (SYSTEM - filtered)

        Expected variables (after filtering system fields):
        Required: name, layer (used in overridden module_docstring block)
        Optional: worker_scope, capabilities, module_description,
                  responsibilities, dependencies

        Total: ~6-8 variables (not just 2 from concrete template alone)
        """
        # Arrange

        template_root = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
        )
        template_path = "concrete/worker.py.jinja2"

        # Act
        schema = introspect_template_with_inheritance(template_root, template_path)

        # Assert - should include variables from parent templates
        all_vars = set(schema.required + schema.optional)

        # Variables from concrete template
        assert "name" in all_vars, "name from concrete template"
        assert "worker_scope" in all_vars, "worker_scope from concrete template"

        # Variables from tier1_base_code (used in overridden module_docstring)
        assert "layer" in all_vars, "layer from tier1 parent template"
        assert "responsibilities" in all_vars, "responsibilities from tier1 parent"

        # Should have MORE than just concrete template variables (was 2, now 6+)
        assert len(all_vars) >= 6, f"Expected 6+ variables, got {len(all_vars)}: {sorted(all_vars)}"

    def test_introspect_with_inheritance_merges_all_tiers(self) -> None:
        """RED: Verify that variables from ALL tiers in chain are detected."""
        # Arrange

        template_root = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
        )
        template_path = "concrete/worker.py.jinja2"

        # Act
        schema = introspect_template_with_inheritance(template_root, template_path)

        # Assert - check specific tier contributions
        all_vars = set(schema.required + schema.optional)

        # Tier1 contributes: layer, dependencies, responsibilities,
        # module_description
        tier1_vars = {
            "layer",
            "dependencies",
            "responsibilities",
            "module_description",
        }
        detected_tier1 = tier1_vars & all_vars
        assert (
            len(detected_tier1) >= 2
        ), f"Should detect tier1 vars, found: {detected_tier1}"

        # Concrete contributes: name, worker_scope, capabilities
        concrete_vars = {"name", "worker_scope", "capabilities"}
        detected_concrete = concrete_vars & all_vars
        assert (
            len(detected_concrete) >= 2
        ), f"Should detect concrete vars, found: {detected_concrete}"

    def test_introspect_with_inheritance_filters_system_fields(self) -> None:
        """RED: Verify system fields from tier0 are still filtered out."""
        # Arrange

        template_root = (
            Path(__file__).parent.parent.parent.parent
            / "mcp_server"
            / "scaffolding"
            / "templates"
        )
        template_path = "concrete/worker.py.jinja2"

        # Act
        schema = introspect_template_with_inheritance(template_root, template_path)

        # Assert - system fields should NOT be in schema
        all_vars = set(schema.required + schema.optional)
        system_fields = {
            "template_id",
            "template_version",
            "scaffold_created",
            "output_path",
            "timestamp",
        }

        assert not (
            system_fields & all_vars
        ), (
            f"System fields should be filtered: "
            f"{system_fields & all_vars}"
        )
