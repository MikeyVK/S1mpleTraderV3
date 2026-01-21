# artifact: type=unit_test, version=1.0, created=2026-01-21T22:10:00Z
"""
E2E test verifying template introspection in scaffold validation flow.

Tests that ValidationError from scaffold_artifact contains schema extracted
via template introspection, with system fields filtered appropriately.

Following TDD: These tests are written BEFORE implementation (RED phase).
@layer: Tests (Integration/E2E)
@dependencies: [pytest, mcp_server.tools.scaffold_artifact,
                mcp_server.core.exceptions]
@responsibilities:
    - Test ValidationError contains schema from template introspection
    - Test schema excludes system-injected fields
    - Test optional fields can be omitted in scaffold
    - Test missing required fields error includes full schema
"""
# Standard library
# (no standard library imports needed)

# Third-party
import pytest

# Project modules
from mcp_server.tools.scaffold_artifact import (
    ScaffoldArtifactInput,
    ScaffoldArtifactTool,
)


class TestScaffoldValidationIntrospection:
    """E2E tests for template introspection in scaffold validation."""

    @pytest.mark.asyncio
    async def test_validation_error_includes_introspected_schema(
        self
    ) -> None:
        """RED: scaffold_artifact ValidationError includes template-introspected schema"""
        # Arrange
        tool = ScaffoldArtifactTool()
        params = ScaffoldArtifactInput(
            artifact_type="dto",
            name="TestDTO",
            # Missing 'description' - required by template
        )

        # Act
        result = await tool.execute(params)

        # Assert - error should include schema from template introspection
        assert result.is_error, "Expected validation error"
        assert result.error_code == "ERR_VALIDATION"
        
        # Check if schema is in resources (structured data)
        schema_resource = None
        for item in result.content:
            if item.get("type") == "resource":
                schema_resource = item
                break
        
        assert schema_resource is not None, "Expected schema resource in error response"
        # Schema should be extracte from template, not artifacts.yaml
        # (We'll verify this works after GREEN implementation)

    @pytest.mark.asyncio
    async def test_error_schema_excludes_system_fields(
        self
    ) -> None:
        """RED: schema in error response excludes system fields (template_id, etc.)"""
        # Arrange
        tool = ScaffoldArtifactTool()
        params = ScaffoldArtifactInput(
            artifact_type="dto",
            name="TestDTO",
            # Missing 'description'
        )

        # Act
        result = await tool.execute(params)

        # Assert - extract schema from resources
        schema_resource = None
        for item in result.content:
            if item.get("type") == "resource" and "schema" in item.get("resource", {}).get("text", ""):
                import json
                schema_data = json.loads(item["resource"]["text"])
                schema_resource = schema_data
                break

        assert schema_resource is not None, "Expected schema in error"
        
        # System fields should NOT be in required or optional lists
        all_fields = (
            schema_resource.get("schema", {}).get("required", []) +
            schema_resource.get("schema", {}).get("optional", [])
        )
        
        system_fields = {"template_id", "template_version", "scaffold_created", "output_path"}
        for sys_field in system_fields:
            assert sys_field not in all_fields, (
                f"System field '{sys_field}' should be filtered from agent schema"
            )

    @pytest.mark.asyncio
    async def test_scaffold_succeeds_with_optional_fields_omitted(
        self
    ) -> None:
        """RED: scaffold succeeds when optional template fields omitted"""
        # Arrange
        tool = ScaffoldArtifactTool()
        params = ScaffoldArtifactInput(
            artifact_type="dto",
            name="TestDTO",
            description="Test DTO",
            # 'frozen' is optional in template ({% if frozen %}) - omit it
        )

        # Act
        result = await tool.execute(params)

        # Assert - should succeed (optional fields not required)
        assert not result.is_error, (
            f"Expected success, got error: {result.content[0].get('text', '')}"
        )
