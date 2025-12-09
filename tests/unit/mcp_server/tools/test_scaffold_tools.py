"""Tests for scaffold tools."""
# pyright: reportUnusedVariable=false
from unittest.mock import MagicMock

import pytest

from mcp_server.core.exceptions import ValidationError
from mcp_server.tools.scaffold_tools import ScaffoldComponentTool, ScaffoldDesignDocTool


class TestScaffoldComponentTool:
    """Tests for ScaffoldComponentTool."""

    @pytest.mark.asyncio
    async def test_scaffold_dto(self) -> None:
        """Test scaffolding a DTO."""
        mock_manager = MagicMock()
        mock_manager.render_dto.return_value = "class TestDTO: pass"
        mock_manager.render_dto_test.return_value = "class TestTestDTO: pass"

        tool = ScaffoldComponentTool(manager=mock_manager)
        result = await tool.execute(
            component_type="dto",
            name="OrderState",
            output_path="backend/dtos/order_state.py",
            fields=[
                {"name": "order_id", "type": "str"},
                {"name": "quantity", "type": "int"}
            ]
        )

        mock_manager.render_dto.assert_called_once()
        mock_manager.write_file.assert_called()
        assert "OrderState" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_scaffold_dto_without_test(self) -> None:
        """Test scaffolding a DTO without test file."""
        mock_manager = MagicMock()
        mock_manager.render_dto.return_value = "class TestDTO: pass"

        tool = ScaffoldComponentTool(manager=mock_manager)
        _ = await tool.execute(
            component_type="dto",
            name="SimpleDTO",
            output_path="backend/dtos/simple.py",
            fields=[{"name": "value", "type": "int"}],
            generate_test=False
        )

        mock_manager.render_dto.assert_called_once()
        mock_manager.render_dto_test.assert_not_called()

    @pytest.mark.asyncio
    async def test_scaffold_dto_requires_fields(self) -> None:
        """Test DTO scaffolding requires fields."""
        tool = ScaffoldComponentTool(manager=MagicMock())

        with pytest.raises(ValidationError, match="Fields are required"):
            await tool.execute(
                component_type="dto",
                name="EmptyDTO",
                output_path="test.py"
            )

    @pytest.mark.asyncio
    async def test_scaffold_worker(self) -> None:
        """Test scaffolding a Worker."""
        mock_manager = MagicMock()
        mock_manager.render_worker.return_value = "class TestWorker: pass"

        tool = ScaffoldComponentTool(manager=mock_manager)
        result = await tool.execute(
            component_type="worker",
            name="OrderProcessor",
            output_path="backend/workers/order_processor.py",
            input_dto="OrderInputDTO",
            output_dto="OrderOutputDTO"
        )

        mock_manager.render_worker.assert_called_once_with(
            name="OrderProcessor",
            input_dto="OrderInputDTO",
            output_dto="OrderOutputDTO"
        )
        assert "OrderProcessor" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_scaffold_worker_requires_dtos(self) -> None:
        """Test Worker scaffolding requires input_dto and output_dto."""
        tool = ScaffoldComponentTool(manager=MagicMock())

        with pytest.raises(ValidationError, match="input_dto and output_dto"):
            await tool.execute(
                component_type="worker",
                name="TestWorker",
                output_path="test.py"
            )

    @pytest.mark.asyncio
    async def test_scaffold_adapter(self) -> None:
        """Test scaffolding an Adapter."""
        mock_manager = MagicMock()
        mock_manager.render_adapter.return_value = "class ExchangeAdapter: pass"

        tool = ScaffoldComponentTool(manager=mock_manager)
        result = await tool.execute(
            component_type="adapter",
            name="Exchange",
            output_path="backend/adapters/exchange.py",
            methods=[
                {"name": "get_price", "params": "symbol: str", "return_type": "Decimal"}
            ]
        )

        mock_manager.render_adapter.assert_called_once()
        assert "Exchange" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_scaffold_adapter_requires_methods(self) -> None:
        """Test Adapter scaffolding requires methods."""
        tool = ScaffoldComponentTool(manager=MagicMock())

        with pytest.raises(ValidationError, match="Methods are required"):
            await tool.execute(
                component_type="adapter",
                name="TestAdapter",
                output_path="test.py"
            )

    @pytest.mark.asyncio
    async def test_scaffold_unknown_type_raises_error(self) -> None:
        """Test unknown component type raises error."""
        tool = ScaffoldComponentTool(manager=MagicMock())

        with pytest.raises(ValidationError, match="Unknown component type"):
            await tool.execute(
                component_type="unknown",
                name="Test",
                output_path="test.py"
            )

    def test_scaffold_tool_schema(self) -> None:
        """Test scaffold tool has correct schema."""
        tool = ScaffoldComponentTool(manager=MagicMock())
        schema = tool.input_schema

        assert "component_type" in schema["properties"]
        assert "name" in schema["properties"]
        assert "output_path" in schema["properties"]
        assert "fields" in schema["properties"]
        assert "component_type" in schema["required"]


class TestScaffoldDesignDocTool:
    """Tests for ScaffoldDesignDocTool."""

    @pytest.mark.asyncio
    async def test_scaffold_design_doc(self) -> None:
        """Test scaffolding a design document."""
        mock_manager = MagicMock()
        mock_manager.render_design_doc.return_value = "# Test Design"

        tool = ScaffoldDesignDocTool(manager=mock_manager)
        result = await tool.execute(
            title="Order Processing Design",
            output_path="docs/design/order_processing.md",
            author="Developer",
            summary="Design for order processing"
        )

        mock_manager.render_design_doc.assert_called_once()
        mock_manager.write_file.assert_called_once()
        assert "order_processing.md" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_scaffold_design_doc_with_sections(self) -> None:
        """Test scaffolding design doc with custom sections."""
        mock_manager = MagicMock()
        mock_manager.render_design_doc.return_value = "# Test"

        tool = ScaffoldDesignDocTool(manager=mock_manager)
        await tool.execute(
            title="Test",
            output_path="docs/test.md",
            sections=["Overview", "Requirements", "Architecture"]
        )

        call_args = mock_manager.render_design_doc.call_args
        assert call_args.kwargs["sections"] == ["Overview", "Requirements", "Architecture"]

    @pytest.mark.asyncio
    async def test_scaffold_design_doc_status(self) -> None:
        """Test scaffolding design doc with status."""
        mock_manager = MagicMock()
        mock_manager.render_design_doc.return_value = "# Test"

        tool = ScaffoldDesignDocTool(manager=mock_manager)
        await tool.execute(
            title="Test",
            output_path="docs/test.md",
            status="REVIEW"
        )

        call_args = mock_manager.render_design_doc.call_args
        assert call_args.kwargs["status"] == "REVIEW"

    def test_design_doc_tool_schema(self) -> None:
        """Test design doc tool has correct schema."""
        tool = ScaffoldDesignDocTool(manager=MagicMock())
        schema = tool.input_schema

        assert "title" in schema["properties"]
        assert "output_path" in schema["properties"]
        assert "sections" in schema["properties"]
        assert "status" in schema["properties"]
        assert "title" in schema["required"]
