"""Unit tests for scaffold_tools.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_server.core.exceptions import ValidationError
from mcp_server.tools.scaffold_tools import (
    ScaffoldComponentTool, ScaffoldComponentInput,
    ScaffoldDesignDocTool, ScaffoldDesignDocInput
)
from mcp_server.tools.base import ToolResult

@pytest.fixture
def mock_scaffold_manager():
    return MagicMock()

@pytest.mark.asyncio
async def test_scaffold_component_dispatch(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="dto",
        name="TestDto",
        output_path="path/to/dto.py",
        fields=[{"name": "field1", "type": "str"}]
    )
    
    # Mock specific handler logic indirectly via manager calls
    mock_scaffold_manager.render_dto.return_value = "content"
    
    result = await tool.execute(params)
    
    mock_scaffold_manager.render_dto.assert_called_once()
    mock_scaffold_manager.write_file.assert_called()
    assert "Scaffolded dto 'TestDto'" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_component_unknown_type(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="unknown_type",
        name="Test",
        output_path="path.py"
    )
    
    with pytest.raises(ValidationError) as exc:
        await tool.execute(params)
    assert "Unknown component type: unknown_type" in str(exc.value)

@pytest.mark.asyncio
async def test_scaffold_worker(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="worker",
        name="TestWorker",
        output_path="worker.py",
        input_dto="InputDto",
        output_dto="OutputDto"
    )
    
    mock_scaffold_manager.render_worker.return_value = "worker_code"
    
    result = await tool.execute(params)
    
    mock_scaffold_manager.render_worker.assert_called_with(
        name="TestWorker", input_dto="InputDto", output_dto="OutputDto"
    )
    assert "Scaffolded worker 'TestWorker'" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_worker_missing_args(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="worker",
        name="TestWorker",
        output_path="worker.py"
        # Missing dtos
    )
    
    with pytest.raises(ValidationError):
        await tool.execute(params)

@pytest.mark.asyncio
async def test_scaffold_adapter(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="adapter",
        name="TestAdapter",
        output_path="adapter.py",
        methods=[{"name": "fetch", "return": "dict"}]
    )
    
    mock_scaffold_manager.render_adapter.return_value = "adapter_code"
    
    await tool.execute(params)
    
    mock_scaffold_manager.render_adapter.assert_called()

@pytest.mark.asyncio
async def test_scaffold_tool_component(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="tool",
        name="TestTool",
        output_path="tool.py",
        input_schema={"type": "object"}
    )
    
    mock_scaffold_manager.render_tool.return_value = "tool_code"
    
    await tool.execute(params)
    mock_scaffold_manager.render_tool.assert_called()

@pytest.mark.asyncio
async def test_scaffold_generic_missing_args(mock_scaffold_manager):
    tool = ScaffoldComponentTool(manager=mock_scaffold_manager)
    params = ScaffoldComponentInput(
        component_type="generic",
        name="Gen",
        output_path="gen.py"
    )
    
    with pytest.raises(ValidationError):
        await tool.execute(params)

@pytest.mark.asyncio
async def test_scaffold_design_doc(mock_scaffold_manager):
    tool = ScaffoldDesignDocTool(manager=mock_scaffold_manager)
    params = ScaffoldDesignDocInput(
        title="My Design",
        output_path="design.md",
        doc_type="design",
        author="Me"
    )
    
    mock_scaffold_manager.render_design_doc.return_value = "# Design"
    
    result = await tool.execute(params)
    
    mock_scaffold_manager.render_design_doc.assert_called_with(
        title="My Design",
        author="Me",
        summary=None,
        sections=None,
        status="DRAFT"
    )
    mock_scaffold_manager.write_file.assert_called_with("design.md", "# Design")
    assert "Created design document: design.md" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_generic_doc(mock_scaffold_manager):
    tool = ScaffoldDesignDocTool(manager=mock_scaffold_manager)
    params = ScaffoldDesignDocInput(
        title="Generic Doc",
        output_path="doc.md",
        doc_type="generic",
        context={"extra": "value"}
    )
    
    mock_scaffold_manager.render_generic_doc.return_value = "content"
    
    await tool.execute(params)
    
    mock_scaffold_manager.render_generic_doc.assert_called()
