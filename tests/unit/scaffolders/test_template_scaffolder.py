# tests/unit/scaffolders/test_template_scaffolder.py
"""
Unit tests for TemplateScaffolder.

Tests unified template-based scaffolding via public API only.

@layer: Tests (Unit)
@dependencies: [
    pytest,
    unittest.mock,
    mcp_server.scaffolders.template_scaffolder,
    mcp_server.scaffolding.renderer,
    mcp_server.core.exceptions
]
"""

# Standard library
from unittest.mock import Mock

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig


@pytest.fixture(name="registry")
def artifact_registry() -> ArtifactRegistryConfig:
    """Provide artifact registry configuration."""
    return ArtifactRegistryConfig.from_file()


@pytest.fixture(name="mock_renderer")
def mock_jinja_renderer() -> Mock:
    """Provide mock JinjaRenderer."""
    renderer = Mock(spec=JinjaRenderer)
    renderer.render.return_value = "class MockContent: pass"
    return renderer


class TestConstructor:
    """Test TemplateScaffolder initialization."""

    def test_accepts_custom_renderer(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Constructor accepts custom renderer via dependency injection."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        # Verify by using it - renderer should be called during scaffold
        result = scaffolder.scaffold(
            artifact_type="dto",
            name="TestDTO",
            description="Test"
        )

        assert result.content == "class MockContent: pass"
        mock_renderer.render.assert_called_once()

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
                artifact_type="dto",
                name="TestDTO"
                # Missing 'description' required field
            )

        error_msg = str(exc_info.value)
        assert "Missing required fields" in error_msg
        assert "description" in error_msg

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
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold DTO renders template with correct path."""
        mock_renderer.render.return_value = "class TestDTO(BaseModel): pass"

        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        result = scaffolder.scaffold(
            artifact_type="dto",
            name="TestDTO",
            description="Test DTO"
        )

        assert result.content == "class TestDTO(BaseModel): pass"
        assert result.file_name == "TestDTO.py"
        mock_renderer.render.assert_called_once()
        template_arg = mock_renderer.render.call_args[0][0]
        assert template_arg == "components/dto.py.jinja2"

    def test_scaffold_worker_includes_name_suffix(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold Worker appends name_suffix to filename."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        result = scaffolder.scaffold(
            artifact_type="worker",
            name="Process",
            input_dto="InputDTO",
            output_dto="OutputDTO"
        )

        assert result.file_name == "ProcessWorker.py"

    def test_scaffold_design_doc_uses_markdown_extension(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold design document uses .md extension."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        result = scaffolder.scaffold(
            artifact_type="design",
            title="Test Design",
            author="Agent",
            issue_number=56
        )

        assert result.file_name == "Test Design.md"

    def test_scaffold_service_orchestrator_selects_correct_template(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold service orchestrator uses correct template."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        scaffolder.scaffold(
            artifact_type="service",
            name="OrderService",
            service_type="orchestrator"
        )

        mock_renderer.render.assert_called_once()
        template_arg = mock_renderer.render.call_args[0][0]
        assert template_arg == "components/service_orchestrator.py.jinja2"

    def test_scaffold_service_command_selects_correct_template(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold service command uses correct template."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        scaffolder.scaffold(
            artifact_type="service",
            name="CreateOrder",
            service_type="command"
        )

        template_arg = mock_renderer.render.call_args[0][0]
        assert template_arg == "components/service_command.py.jinja2"

    def test_scaffold_service_defaults_to_orchestrator(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold service without service_type defaults to orchestrator."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        scaffolder.scaffold(
            artifact_type="service",
            name="DefaultService"
        )

        template_arg = mock_renderer.render.call_args[0][0]
        assert template_arg == "components/service_orchestrator.py.jinja2"

    def test_scaffold_generic_uses_template_name_from_context(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold generic artifact uses template_name from context."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        scaffolder.scaffold(
            artifact_type="generic",
            name="CustomComponent",
            template_name="custom/my_template.py.jinja2",
            output_path="custom/component.py"
        )

        template_arg = mock_renderer.render.call_args[0][0]
        assert template_arg == "custom/my_template.py.jinja2"

    def test_scaffold_generic_without_template_name_fails(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold generic without template_name raises ValidationError."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        with pytest.raises(ValidationError) as exc_info:
            scaffolder.scaffold(
                artifact_type="generic",
                name="Broken",
                output_path="broken.py"
            )

        assert "template_name" in str(exc_info.value).lower()

    def test_scaffold_passes_all_context_to_renderer(
        self,
        registry: ArtifactRegistryConfig,
        mock_renderer: Mock
    ) -> None:
        """Scaffold passes all context fields to template renderer."""
        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=mock_renderer
        )

        scaffolder.scaffold(
            artifact_type="dto",
            name="UserDTO",
            description="User data",
            fields=[{"name": "id", "type": "int"}],
            docstring="Custom docstring"
        )

        render_kwargs = mock_renderer.render.call_args[1]
        assert render_kwargs["name"] == "UserDTO"
        assert render_kwargs["description"] == "User data"
        assert "fields" in render_kwargs
        assert render_kwargs["docstring"] == "Custom docstring"

    def test_scaffold_template_not_found_raises_execution_error(
        self,
        registry: ArtifactRegistryConfig
    ) -> None:
        """Scaffold with missing template raises ExecutionError (not ValidationError)."""
        failing_renderer = Mock(spec=JinjaRenderer)
        failing_renderer.render.side_effect = ExecutionError(
            "Template not found",
            recovery=["Check template path in artifacts.yaml"]
        )

        scaffolder = TemplateScaffolder(
            registry=registry,
            renderer=failing_renderer
        )

        # ExecutionError propagates (semantically correct - template loading is execution)
        with pytest.raises(ExecutionError) as exc_info:
            scaffolder.scaffold(
                artifact_type="dto",
                name="TestDTO",
                description="Test"
            )

        assert "Template not found" in str(exc_info.value)
