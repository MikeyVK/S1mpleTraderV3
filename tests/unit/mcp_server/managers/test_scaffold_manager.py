"""Tests for ScaffoldManager - template-driven code generation."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.managers.scaffold_manager import ScaffoldManager


class TestScaffoldManagerInit:
    """Tests for ScaffoldManager initialization."""

    def test_init_with_default_template_dir(self) -> None:
        """Test manager initializes with default template directory."""
        manager = ScaffoldManager()
        assert manager.template_dir is not None
        assert "templates" in str(manager.template_dir)

    def test_init_with_custom_template_dir(self) -> None:
        """Test manager initializes with custom template directory."""
        manager = ScaffoldManager(template_dir=Path("/custom/templates"))
        assert manager.template_dir == Path("/custom/templates")


class TestScaffoldManagerTemplateLoading:
    """Tests for template loading functionality."""

    def test_load_template_success(self) -> None:
        """Test loading an existing template."""
        with patch("jinja2.Environment.get_template") as mock_get:
            mock_template = MagicMock()
            mock_get.return_value = mock_template

            manager = ScaffoldManager()
            template = manager.get_template("components/dto.py.jinja2")

            assert template is not None

    def test_load_template_not_found_raises_error(self) -> None:
        """Test loading non-existent template raises error."""
        from jinja2.exceptions import TemplateNotFound

        with patch("jinja2.Environment.get_template") as mock_get:
            mock_get.side_effect = TemplateNotFound("nonexistent.jinja2")

            manager = ScaffoldManager()

            with pytest.raises(ExecutionError, match="Template not found"):
                manager.get_template("nonexistent.jinja2")

    def test_list_available_templates(self) -> None:
        """Test listing available templates."""
        manager = ScaffoldManager()
        templates = manager.list_templates()

        assert isinstance(templates, list)


class TestScaffoldManagerRenderDTO:
    """Tests for DTO scaffolding."""

    def test_render_dto_basic(self) -> None:
        """Test rendering a basic DTO."""
        manager = ScaffoldManager()
        result = manager.render_dto(
            name="OrderState",
            fields=[
                {"name": "order_id", "type": "str"},
                {"name": "quantity", "type": "int"},
                {"name": "price", "type": "Decimal"},
            ]
        )

        assert "OrderState" in result
        assert "BaseModel" in result  # Pydantic
        assert '"frozen": True' in result  # Pydantic model_config dict
        assert "order_id: str" in result

    def test_render_dto_with_docstring(self) -> None:
        """Test DTO includes docstring."""
        manager = ScaffoldManager()
        result = manager.render_dto(
            name="TestDTO",
            fields=[{"name": "value", "type": "int"}],
            docstring="A test DTO for testing."
        )

        assert "A test DTO for testing." in result

    def test_render_dto_with_optional_fields(self) -> None:
        """Test DTO with optional fields."""
        manager = ScaffoldManager()
        result = manager.render_dto(
            name="ConfigDTO",
            fields=[
                {"name": "required", "type": "str"},
                {"name": "optional", "type": "int", "default": "None", "optional": True},
            ]
        )

        assert "optional: int | None = None" in result or "Optional[int]" in result

    def test_render_dto_invalid_name_raises_error(self) -> None:
        """Test invalid DTO name raises ValidationError."""
        manager = ScaffoldManager()

        with pytest.raises(ValidationError, match="Invalid"):
            manager.render_dto(
                name="invalid-name",  # Not PascalCase
                fields=[{"name": "x", "type": "int"}]
            )


class TestScaffoldManagerRenderWorker:
    """Tests for Worker scaffolding."""

    def test_render_worker_basic(self) -> None:
        """Test rendering a basic Worker."""
        manager = ScaffoldManager()
        result = manager.render_worker(
            name="OrderProcessor",
            input_dto="OrderInputDTO",
            output_dto="OrderOutputDTO"
        )

        assert "class OrderProcessorWorker" in result or "class OrderProcessor" in result
        assert "BaseWorker" in result
        assert "async def process" in result

    def test_render_worker_with_dependencies(self) -> None:
        """Test Worker with injected dependencies."""
        manager = ScaffoldManager()
        result = manager.render_worker(
            name="DataFetcher",
            input_dto="FetchRequest",
            output_dto="FetchResponse",
            dependencies=["api_client: APIClient", "cache: CacheService"]
        )

        assert "api_client" in result
        assert "cache" in result


class TestScaffoldManagerRenderAdapter:
    """Tests for Adapter scaffolding."""

    def test_render_adapter_basic(self) -> None:
        """Test rendering a basic Adapter."""
        manager = ScaffoldManager()
        result = manager.render_adapter(
            name="Exchange",
            methods=[
                {"name": "get_price", "params": "symbol: str", "return_type": "Decimal"},
                {"name": "place_order", "params": "order: OrderDTO", "return_type": "OrderResult"},
            ]
        )

        assert "class ExchangeAdapter" in result
        assert "def get_price" in result
        assert "def place_order" in result


class TestScaffoldManagerRenderTest:
    """Tests for test file scaffolding."""

    def test_render_dto_test(self) -> None:
        """Test rendering a test file for a DTO."""
        manager = ScaffoldManager()
        result = manager.render_dto_test(
            dto_name="OrderState",
            module_path="backend.dtos.execution.order_state"
        )

        assert "class TestOrderState" in result
        assert "def test_" in result
        assert "import" in result


class TestScaffoldManagerRenderDesignDoc:
    """Tests for design document scaffolding."""

    def test_render_design_doc(self) -> None:
        """Test rendering a design document."""
        manager = ScaffoldManager()
        result = manager.render_design_doc(
            title="Order Processing System",
            author="Developer",
            summary="Design for the order processing pipeline",
            sections=["Requirements", "Architecture", "Implementation"]
        )

        assert "# Order Processing System" in result
        assert "Requirements" in result
        assert "Architecture" in result

    def test_render_design_doc_with_status(self) -> None:
        """Test design doc includes status badge."""
        manager = ScaffoldManager()
        result = manager.render_design_doc(
            title="Test Design",
            status="DRAFT"
        )

        assert "DRAFT" in result


class TestScaffoldManagerWriteFile:
    """Tests for file writing functionality."""

    def test_write_to_workspace(self) -> None:
        """Test writing generated content to workspace."""
        with patch("pathlib.Path.mkdir"), patch("builtins.open", MagicMock()):
            manager = ScaffoldManager()
            result = manager.write_file(
                path="backend/dtos/test.py",
                content="# Generated content"
            )

            assert result is True or "created" in str(result).lower()

    def test_write_refuses_overwrite_without_flag(self) -> None:
        """Test writing refuses to overwrite existing files."""
        with patch("pathlib.Path.exists", return_value=True):
            manager = ScaffoldManager()

            with pytest.raises(ExecutionError, match="exists"):
                manager.write_file(
                    path="existing/file.py",
                    content="New content",
                    overwrite=False
                )

    def test_write_allows_overwrite_with_flag(self) -> None:
        """Test writing allows overwrite when flag is set."""
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                manager = ScaffoldManager()
                result = manager.write_file(
                    path="existing/file.py",
                    content="New content",
                    overwrite=True
                )

                assert result is True or "created" in str(result).lower()
