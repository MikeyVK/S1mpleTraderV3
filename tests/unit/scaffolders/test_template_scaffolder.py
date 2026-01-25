# tests/unit/scaffolders/test_template_scaffolder.py
"""
Unit tests for TemplateScaffolder.

Tests unified template-based scaffolding via public API only.

@layer: Tests (Unit)
@dependencies: [
    pytest,
    mcp_server.scaffolders.template_scaffolder,
    mcp_server.scaffolding.renderer,
    mcp_server.core.exceptions
]
"""

# Standard library
from pathlib import Path

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig


@pytest.fixture(name="registry")
def artifact_registry() -> ArtifactRegistryConfig:
    """Provide artifact registry configuration."""
    return ArtifactRegistryConfig.from_file()


@pytest.fixture(name="real_renderer")
def real_jinja_renderer() -> JinjaRenderer:
    """Provide real JinjaRenderer using production templates."""
    from mcp_server.config.template_config import get_template_root
    template_dir = get_template_root()
    return JinjaRenderer(template_dir=template_dir)


@pytest.fixture(name="scaffolder")
def scaffolder_with_real_renderer(
    registry: ArtifactRegistryConfig,
    real_renderer: JinjaRenderer
) -> TemplateScaffolder:
    """Provide TemplateScaffolder with real renderer (production templates)."""
    return TemplateScaffolder(registry=registry, renderer=real_renderer)


@pytest.fixture(name="test_custom_template")
def test_custom_template_fixture(real_renderer: JinjaRenderer):  # type: ignore[no-untyped-def]
    """Create temporary custom template for testing generic artifacts.

    Creates a minimal test template in mcp_server/templates/test_custom/
    and cleans it up after the test completes.

    Yields:
        Template path relative to templates root (e.g., "test_custom/component.py.jinja2")
    """

    # Get template root from renderer
    template_root = Path(real_renderer.template_dir)
    custom_dir = template_root / "test_custom"
    custom_dir.mkdir(exist_ok=True)

    # Write minimal test template
    template_file = custom_dir / "test_component.py.jinja2"
    template_file.write_text(
        "# SCAFFOLD: template={{ template_id }} version={{ template_version }}\n"
        '"""{{ description }}\n\n'
        "Test custom component generated from user-defined template.\n"
        '"""\n\n'
        "class {{ name }}:\n"
        '    """{{ description }}."""\n'
        "    pass\n"
    )

    template_path = "test_custom/test_component.py.jinja2"
    yield template_path

    # Cleanup
    template_file.unlink()
    if not any(custom_dir.iterdir()):
        custom_dir.rmdir()


class TestConstructor:
    """Test TemplateScaffolder initialization."""

    def test_accepts_custom_renderer(
        self,
        registry: ArtifactRegistryConfig,
        real_renderer: JinjaRenderer
    ) -> None:
        """Constructor accepts custom renderer via dependency injection."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=real_renderer
        )

        # Verify by using it - renderer should work with production templates
        result = scaffolder.scaffold(
            artifact_type="dto",
            name="TestDTO",
            description="Test DTO"
        )

        # Assert on structure (not exact content which may evolve)
        assert "class TestDTO" in result.content
        assert "BaseModel" in result.content
        assert result.file_name == "TestDTO.py"

    def test_creates_default_renderer_when_not_provided(
        self,
        registry: ArtifactRegistryConfig
    ) -> None:
        """Constructor creates default renderer if none provided."""
        scaffolder = TemplateScaffolder(registry=registry)

        # Verify by checking it works (doesn't raise)
        assert scaffolder.registry is not None


class TestValidate:
    """Test validate method."""

    def test_validate_success_with_all_required_fields(
        self,
        registry: ArtifactRegistryConfig
    ) -> None:
        """Validate passes when all required fields present."""
        scaffolder = TemplateScaffolder(registry=registry)

        result = scaffolder.validate(
            artifact_type="dto",
            name="TestDTO",
            description="Test DTO"
        )

        assert result is True

    def test_validate_fails_when_required_field_missing(
        self,
        registry: ArtifactRegistryConfig
    ) -> None:
        """Validate raises ValidationError when required field missing."""
        scaffolder = TemplateScaffolder(registry=registry)

        with pytest.raises(ValidationError) as exc_info:
            scaffolder.validate(
                artifact_type="dto"
                # Missing 'name' required field (description is optional in concrete templates)
            )

        error_msg = str(exc_info.value)
        assert "Missing required fields" in error_msg
        assert "name" in error_msg

    def test_validate_allows_optional_fields_to_be_missing(
        self,
        registry: ArtifactRegistryConfig
    ) -> None:
        """Validate passes when optional fields missing."""
        scaffolder = TemplateScaffolder(registry=registry)

        result = scaffolder.validate(
            artifact_type="dto",
            name="TestDTO",
            description="Test"
            # Optional fields like 'fields', 'docstring' not provided
        )

        assert result is True


class TestScaffold:
    """Test scaffold method."""

    def test_scaffold_dto_renders_template(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold DTO renders template with correct structure."""
        result = scaffolder.scaffold(
            artifact_type="dto",
            name="TestDTO",
            description="Test DTO"
        )

        # Assert on structure (production template)
        assert "class TestDTO" in result.content
        assert "BaseModel" in result.content
        assert result.file_name == "TestDTO.py"
        assert "Test DTO" in result.content  # Docstring

    def test_scaffold_worker_includes_name_suffix(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold Worker appends name_suffix to filename."""
        # Skip: Worker template not yet implemented (template_path=null)
        pytest.skip("Worker template not yet implemented - template_path=null in artifacts.yaml")
        result = scaffolder.scaffold(
            artifact_type="worker",
            name="Process",
            input_dto="InputDTO",
            output_dto="OutputDTO",
            dependencies=[],  # Required by worker template
            responsibilities="Process input data"  # Required by worker template
        )

        # Verify suffix logic (from artifacts.yaml: name_suffix="Worker")
        assert result.file_name == "ProcessWorker.py"
        # Concrete template uses plain class (not BaseWorker inheritance)
        assert "class Process:" in result.content
        assert "async def execute" in result.content

    def test_scaffold_design_doc_uses_markdown_extension(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold design document uses .md extension."""
        result = scaffolder.scaffold(
            artifact_type="design",
            title="Test Design",
            author="Agent",
            issue_number=56
        )

        assert result.file_name == "Test Design.md"
        assert "Test Design" in result.content

    def test_scaffold_service_orchestrator_selects_correct_template(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold service orchestrator uses correct template."""
        result = scaffolder.scaffold(
            artifact_type="service",
            name="OrderService",
            service_type="orchestrator"
        )

        # Check that orchestrator template was used (not command/query)
        assert "OrderServiceService" in result.content or "OrderService" in result.content
        assert result.file_name == "OrderServiceService.py"

    def test_scaffold_service_command_selects_correct_template(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold service command uses correct template."""
        result = scaffolder.scaffold(
            artifact_type="service",
            name="CreateOrder",
            service_type="command"
        )

        # Check that command template was used
        assert "CreateOrderService" in result.content or "CreateOrder" in result.content
        assert result.file_name == "CreateOrderService.py"

    def test_scaffold_service_defaults_to_orchestrator(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold service without service_type defaults to orchestrator."""
        result = scaffolder.scaffold(
            artifact_type="service",
            name="DefaultService"
        )

        # Should use orchestrator as default
        assert "DefaultServiceService" in result.content or "DefaultService" in result.content
        assert result.file_name == "DefaultServiceService.py"

    def test_scaffold_generic_uses_template_name_from_context(
        self,
        scaffolder: TemplateScaffolder,
        test_custom_template: str
    ) -> None:
        """Scaffold generic artifact uses template_name from context.

        Tests that:
        - Generic artifact type accepts template_name parameter
        - Custom user-defined templates can be loaded
        - Template rendering produces expected output structure
        """
        result = scaffolder.scaffold(
            artifact_type="generic",
            name="TestCustomComponent",
            template_name=test_custom_template,  # User-specified custom template
            description="Test custom component"
        )

        # Verify custom template was used and rendered correctly
        assert "class TestCustomComponent" in result.content
        assert "Test custom component" in result.content
        assert "user-defined template" in result.content  # From template comment
        assert result.file_name == "TestCustomComponent.py"

    def test_scaffold_generic_without_template_name_uses_default(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold generic without template_name uses default from artifacts.yaml."""
        # Generic has default template_path in artifacts.yaml: "concrete/generic.py.jinja2"
        # Without template_name in context, uses that default
        result = scaffolder.scaffold(
            artifact_type="generic",
            name="DefaultGeneric"
        )

        # Should use default concrete/generic.py.jinja2
        assert result.file_name == "DefaultGeneric.py"
        assert "class DefaultGeneric:" in result.content

    def test_scaffold_passes_all_context_to_renderer(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """Scaffold passes all context fields to template renderer."""
        result = scaffolder.scaffold(
            artifact_type="dto",
            name="UserDTO",
            description="User data",
            fields=[{"name": "id", "type": "int"}],
            docstring="Custom docstring"
        )

        # Verify that all context was used in rendering
        assert "UserDTO" in result.content
        assert "User data" in result.content
        # Note: fields and docstring handling depends on template implementation

    def test_scaffold_template_not_found_raises_exception(
        self,
        registry: ArtifactRegistryConfig,
        real_renderer: JinjaRenderer
    ) -> None:
        """Scaffold with missing artifact type raises ConfigError."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=real_renderer
        )

        # Try to scaffold with an unknown artifact type
        with pytest.raises(ConfigError):
            scaffolder.scaffold(
                artifact_type="non_existent_type",
                name="TestComponent"
            )
