"""Behavioral tests: No hardcoded template fallbacks.
Tests verify that template resolution uses ONLY artifacts.yaml configuration,
with no hardcoded fallbacks to legacy "components/" paths.
Test Strategy: Use public API (scaffold()) and verify behavior through:
- Successfully scaffolded content
- Template metadata in output
- Error messages when templates missing
This approach tests behavior, not implementation details, making tests:
- Robust against refactoring
- Self-documenting of expected behavior
- Focused on user-visible outcomes
@layer: Tests (Unit - Behavioral)
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.config.artifact_registry_config import (
    ArtifactDefinition,
    ArtifactRegistryConfig,
)
from mcp_server.config.template_config import get_template_root
from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder


class TestServiceTemplateResolution:
    """Service artifacts use ONLY artifacts.yaml template paths."""

    def test_service_scaffolds_successfully_with_artifacts_yaml_template(self) -> None:
        """Service scaffold succeeds using template_path from artifacts.yaml."""
        # Arrange: Load real registry (has service with concrete/service_command.py.jinja2)
        registry = ArtifactRegistryConfig.from_file()
        scaffolder = TemplateScaffolder(registry=registry)
        # Act: Scaffold service (should use artifacts.yaml template)
        result = scaffolder.scaffold(
            artifact_type="service",
            name="ProcessOrder",
            description="Process customer orders",
            service_type="command",
            input_dto="OrderRequest",
            output_dto="OrderResponse",
            output_path="backend/services/ProcessOrderService.py",
        )
        # Assert: Successfully scaffolded using correct template
        assert result.content is not None
        assert len(result.content) > 0
        assert "ProcessOrder" in result.content
        assert "Process customer orders" in result.content
        # Verify template metadata is present (2-line format)
        lines = result.content.strip().split("\n")
        assert lines[0].startswith("# "), "Line 1 should be commented filepath"
        assert "template=" in lines[1], "Line 2 should have metadata"
        # If hardcoded fallback to components/ was active, this would fail
        # because template wouldn't exist or would have different structure


class TestGenericTemplateResolution:
    """Generic artifacts support context override with template_name."""

    def test_generic_scaffolds_with_default_template_from_artifacts_yaml(self) -> None:
        """Generic without template_name uses artifacts.yaml default."""
        # Arrange
        registry = ArtifactRegistryConfig.from_file()
        scaffolder = TemplateScaffolder(registry=registry)
        # Act: Scaffold generic WITHOUT template_name (use default)
        result = scaffolder.scaffold(
            artifact_type="generic",
            name="CustomComponent",
            description="A custom component",
            output_path="src/components/CustomComponent.py",
        )
        # Assert: Successfully used default template
        assert result.content is not None
        assert "CustomComponent" in result.content
        # Default generic template should have basic structure
        assert "class CustomComponent" in result.content or "CustomComponent" in result.content

    def test_generic_with_custom_template_uses_context_override(self) -> None:
        """Generic with template_name context uses specified template."""
        # Arrange: Create custom template for testing
        registry = ArtifactRegistryConfig.from_file()
        scaffolder = TemplateScaffolder(registry=registry)
        # Get template root and create custom template
        template_root = Path(get_template_root())
        custom_dir = template_root / "test_custom"
        custom_dir.mkdir(exist_ok=True)
        custom_template = custom_dir / "special_component.py.jinja2"
        custom_template.write_text(
            "# CUSTOM TEMPLATE TEST\n"
            "class {{ name }}:\n"
            '    """{{ description }}."""\n'
            "    # Custom template was used!\n"
            "    pass\n"
        )
        try:
            # Act: Scaffold with custom template_name
            result = scaffolder.scaffold(
                artifact_type="generic",
                name="SpecialComponent",
                description="Uses custom template",
                template_name="test_custom/special_component.py.jinja2",
                output_path="src/components/SpecialComponent.py",
            )
            # Assert: Custom template was used (verify unique marker)
            assert result.content is not None
            assert "CUSTOM TEMPLATE TEST" in result.content
            assert "SpecialComponent" in result.content
            assert "Custom template was used!" in result.content
        finally:
            # Cleanup
            custom_template.unlink()
            if not any(custom_dir.iterdir()):
                custom_dir.rmdir()

    def test_generic_without_template_raises_validation_error(self) -> None:
        """Generic with no template_path in artifacts.yaml and no context fails."""
        # Arrange: Mock registry with generic artifact that has no template
        artifact = Mock(spec=ArtifactDefinition)
        artifact.type_id = "generic"
        artifact.template_path = None  # No default template!
        artifact.fallback_template = None
        artifact.output_type = "file"
        registry = Mock(spec=ArtifactRegistryConfig)
        registry.get_artifact.return_value = artifact
        scaffolder = TemplateScaffolder(registry=registry)
        # Act & Assert: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            scaffolder.scaffold(
                artifact_type="generic",
                name="TestComponent",
                description="Should fail",
                output_path="src/components/TestComponent.py",
                # NO template_name provided!
            )
        # Verify error message is helpful
        assert "template_name" in str(exc_info.value).lower()


class TestNoLegacyComponentsFallback:
    """Verify no hardcoded fallbacks to legacy 'components/' directory."""

    def test_all_artifacts_use_concrete_templates(self) -> None:
        """All artifacts must use concrete/ templates - NO components/ allowed."""
        # Arrange
        registry = ArtifactRegistryConfig.from_file()
        # Act & Assert: STRICT - components/ is NOT allowed (clean break)
        for artifact in registry.artifact_types:
            if artifact.template_path:
                # CLEAN BREAK: No components/ paths allowed
                assert not artifact.template_path.startswith("components/"), (
                    f"CLEAN BREAK VIOLATION: Artifact '{artifact.type_id}' still uses "
                    f"legacy components/ path: {artifact.template_path}\n"
                    f"All templates must use concrete/ or docs/ directories."
                )
                # Verify uses approved paths
                assert (
                    artifact.template_path.startswith("concrete/")
                    or artifact.template_path.startswith("docs/")
                    or artifact.template_path.startswith("test_")  # Test templates ok
                ), (
                    f"Artifact '{artifact.type_id}' uses unexpected template path: "
                    f"{artifact.template_path}\n"
                    f"Expected: concrete/*, docs/*, or test_*"
                )
